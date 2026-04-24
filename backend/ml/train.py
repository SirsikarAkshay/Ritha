"""
Training script for the Ritha fashion recommendation model.

Trains two artefacts:
  1. A MobileNetV2 classifier (13 clothing categories) — saved as fashion_classifier.pth
  2. A category co-occurrence / compatibility matrix    — saved as compatibility.pkl

Usage:
    python -m ml.train                              # from backend/
    python -m ml.train --epochs 15 --batch 32       # custom
"""
import argparse
import os
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image
from sklearn.preprocessing import normalize
import joblib

from ml.categories import (
    DATASET_CATEGORIES, CATEGORY_TO_IDX, NUM_CATEGORIES, IDX_TO_CATEGORY,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR    = Path(__file__).resolve().parent.parent
DATA_DIR    = BASE_DIR / 'data' / 'deep_fashion'
MODEL_DIR   = BASE_DIR / 'ml' / 'artifacts'
CSV_PATH    = DATA_DIR / 'purchase_history.csv'
IMAGE_DIRS  = {
    'train': DATA_DIR / 'images' / 'train',
    'val':   DATA_DIR / 'images' / 'val',
    'test':  DATA_DIR / 'images' / 'test',
}


# ── Dataset ──────────────────────────────────────────────────────────────────

class FashionDataset(Dataset):
    """PyTorch dataset that loads images from train/val/test folders
    and assigns labels from the purchase_history CSV."""

    def __init__(self, image_dir: Path, df: pd.DataFrame, transform=None):
        self.transform = transform
        self.samples = []

        # Build filename → category mapping from CSV
        file_cats = df.groupby('file_name')['category'].first().to_dict()

        for img_path in sorted(image_dir.glob('*.jpg')):
            fname = img_path.name
            cat = file_cats.get(fname)
            if cat and cat in CATEGORY_TO_IDX:
                self.samples.append((img_path, CATEGORY_TO_IDX[cat]))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert('RGB')
        if self.transform:
            img = self.transform(img)
        return img, label


# ── Model ────────────────────────────────────────────────────────────────────

def build_model(num_classes: int = NUM_CATEGORIES, pretrained: bool = True) -> nn.Module:
    """MobileNetV2 with a custom classification head."""
    weights = models.MobileNet_V2_Weights.DEFAULT if pretrained else None
    model = models.mobilenet_v2(weights=weights)
    model.classifier = nn.Sequential(
        nn.Dropout(0.2),
        nn.Linear(model.last_channel, num_classes),
    )
    return model


# ── Training ─────────────────────────────────────────────────────────────────

def train_classifier(epochs: int = 10, batch_size: int = 32, lr: float = 1e-3):
    device = torch.device('mps' if torch.backends.mps.is_available()
                          else 'cuda' if torch.cuda.is_available() else 'cpu')
    logger.info('Using device: %s', device)

    df = pd.read_csv(CSV_PATH)
    logger.info('Loaded %d purchase records', len(df))

    train_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    train_ds = FashionDataset(IMAGE_DIRS['train'], df, transform=train_tf)
    val_ds   = FashionDataset(IMAGE_DIRS['val'],   df, transform=val_tf)
    logger.info('Train: %d images, Val: %d images', len(train_ds), len(val_ds))

    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=0)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=0)

    model = build_model().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

    best_acc = 0.0
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    save_path = MODEL_DIR / 'fashion_classifier.pth'

    for epoch in range(1, epochs + 1):
        # Train
        model.train()
        running_loss, correct, total = 0.0, 0, 0
        for imgs, labels in train_dl:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            out = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * imgs.size(0)
            correct += (out.argmax(1) == labels).sum().item()
            total += imgs.size(0)

        train_acc = correct / total if total else 0
        train_loss = running_loss / total if total else 0

        # Validate
        model.eval()
        val_correct, val_total = 0, 0
        with torch.no_grad():
            for imgs, labels in val_dl:
                imgs, labels = imgs.to(device), labels.to(device)
                out = model(imgs)
                val_correct += (out.argmax(1) == labels).sum().item()
                val_total += imgs.size(0)

        val_acc = val_correct / val_total if val_total else 0
        scheduler.step()

        logger.info(
            'Epoch %2d/%d — loss: %.4f  train_acc: %.2f%%  val_acc: %.2f%%',
            epoch, epochs, train_loss, train_acc * 100, val_acc * 100,
        )

        if val_acc >= best_acc:
            best_acc = val_acc
            torch.save({
                'model_state_dict': model.state_dict(),
                'categories': DATASET_CATEGORIES,
                'num_classes': NUM_CATEGORIES,
                'best_val_acc': best_acc,
            }, save_path)

    logger.info('Best val accuracy: %.2f%% — saved to %s', best_acc * 100, save_path)
    return model


# ── Compatibility Matrix ─────────────────────────────────────────────────────

def build_compatibility_matrix():
    """
    Build a category co-occurrence matrix from purchase history.
    Users who purchase items of category A and category B together
    indicate those categories are compatible in an outfit.
    """
    df = pd.read_csv(CSV_PATH)

    # Group categories per user-image (items worn together in an outfit image)
    grouped = df.groupby(['user_id', 'image_id'])['category'].apply(list).reset_index()

    # Build co-occurrence counts
    cooccurrence = np.zeros((NUM_CATEGORIES, NUM_CATEGORIES), dtype=np.float64)

    for _, row in grouped.iterrows():
        cats = [c for c in row['category'] if c in CATEGORY_TO_IDX]
        idxs = [CATEGORY_TO_IDX[c] for c in cats]
        for i in idxs:
            for j in idxs:
                cooccurrence[i][j] += 1

    # Normalize rows → probability of co-occurrence
    row_sums = cooccurrence.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # avoid division by zero
    compatibility = cooccurrence / row_sums

    # Save
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    artifact = {
        'matrix':     compatibility,
        'categories': DATASET_CATEGORIES,
        'cat_to_idx': CATEGORY_TO_IDX,
        'idx_to_cat': IDX_TO_CATEGORY,
    }
    save_path = MODEL_DIR / 'compatibility.pkl'
    joblib.dump(artifact, save_path)
    logger.info('Compatibility matrix saved to %s', save_path)

    # Log top compatibilities
    logger.info('Top category co-occurrences:')
    for i in range(NUM_CATEGORIES):
        top_j = np.argsort(compatibility[i])[::-1][:3]
        pairs = [(IDX_TO_CATEGORY[j], f'{compatibility[i][j]:.2f}') for j in top_j if j != i]
        if pairs:
            logger.info('  %s → %s', DATASET_CATEGORIES[i], pairs)

    return compatibility


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Train Ritha fashion model')
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--batch',  type=int, default=32)
    parser.add_argument('--lr',     type=float, default=1e-3)
    parser.add_argument('--skip-classifier', action='store_true',
                        help='Skip CNN training, only build compatibility matrix')
    args = parser.parse_args()

    if not args.skip_classifier:
        logger.info('=== Training Fashion Classifier ===')
        train_classifier(epochs=args.epochs, batch_size=args.batch, lr=args.lr)

    logger.info('=== Building Compatibility Matrix ===')
    build_compatibility_matrix()

    logger.info('=== Done! Artifacts saved to %s ===', MODEL_DIR)


if __name__ == '__main__':
    main()
