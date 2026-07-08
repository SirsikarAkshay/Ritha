# Starter-pack seed images

Cached **CC0 / public-domain** flat-lay photos used to make freshly-onboarded
wardrobes (and the demo account) look populated with real photos instead of
category illustrations.

## Layout

```
seed_images/
  <region_code>/<gender>/<subcategory>.jpg   # e.g. south_asian_north/women/kurta.jpg
  CREDITS.json                               # provenance for every fetched image
```

`<region_code>`, `<gender>`, and `<subcategory>` come straight from
`wardrobe/data/starter_packs.yaml`. The filename is the slugified `subcategory`.

## How to populate it

Run on a machine with internet access (the fetch uses the Openverse API and
only requests CC0 / Public-Domain-Mark results, so no attribution is required):

```bash
python manage.py fetch_starter_images                                   # everything
python manage.py fetch_starter_images --region south_asian_north --gender women
python manage.py fetch_starter_images --dry-run                         # preview the plan
python manage.py fetch_starter_images --refresh                         # re-fetch cached
```

Then **review the images**, replace any poor matches by hand (search relevance
varies — just drop a better `<subcategory>.jpg` in place), and commit them.

## How they're used

- `seed_starter_packs` copies each cached image into media storage and points
  `StarterPackItem.preview_image_url` at it → the onboarding preview shows photos.
- Onboarding **apply** attaches the cached image to each created `ClothingItem`
  → the applied wardrobe shows real photos everywhere the app renders `image_url`.
- Missing an image? Everything falls back to `/wardrobe-defaults/<category>.svg`.

Images are intentionally small (≤640 px JPEG) to keep the repo light.
