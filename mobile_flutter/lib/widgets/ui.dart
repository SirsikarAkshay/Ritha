import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

// ── Card ────────────────────────────────────────────────────────────────────
class ACard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? background;
  const ACard({super.key, required this.child, this.padding = const EdgeInsets.all(20), this.background});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: background ?? AppColors.surface1,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: child,
    );
  }
}

// ── Card label ──────────────────────────────────────────────────────────────
class CardLabel extends StatelessWidget {
  final String text;
  const CardLabel(this.text, {super.key});

  @override
  Widget build(BuildContext context) => Text(
        text.toUpperCase(),
        style: const TextStyle(
          color: AppColors.creamDim,
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.8,
        ),
      );
}

// ── Badge ───────────────────────────────────────────────────────────────────
enum BadgeVariant { terra, sky, sage, gold }

class ABadge extends StatelessWidget {
  final String text;
  final BadgeVariant variant;
  const ABadge({super.key, required this.text, this.variant = BadgeVariant.sky});

  @override
  Widget build(BuildContext context) {
    late Color bg, fg;
    switch (variant) {
      case BadgeVariant.terra: bg = AppColors.terraDim; fg = AppColors.terraLight; break;
      case BadgeVariant.sky:   bg = const Color(0x1F6FA8C7); fg = AppColors.sky; break;
      case BadgeVariant.sage:  bg = AppColors.sageDim; fg = AppColors.sage; break;
      case BadgeVariant.gold:  bg = AppColors.goldDim; fg = AppColors.gold; break;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(100)),
      child: Text(text, style: TextStyle(color: fg, fontSize: 11, fontWeight: FontWeight.w500)),
    );
  }
}

// ── Labeled input ───────────────────────────────────────────────────────────
class LabeledInput extends StatelessWidget {
  final String label;
  final String? hint;
  final TextEditingController controller;
  final bool obscure;
  final TextInputType? keyboardType;
  final int maxLines;
  final String? Function(String?)? validator;
  final bool enabled;

  const LabeledInput({
    super.key,
    required this.label,
    required this.controller,
    this.hint,
    this.obscure = false,
    this.keyboardType,
    this.maxLines = 1,
    this.validator,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label.toUpperCase(),
            style: const TextStyle(
              color: AppColors.creamDim,
              fontSize: 11,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 6),
          TextFormField(
            controller: controller,
            obscureText: obscure,
            keyboardType: keyboardType,
            maxLines: obscure ? 1 : maxLines,
            validator: validator,
            enabled: enabled,
            style: const TextStyle(color: AppColors.cream, fontSize: 15),
            decoration: InputDecoration(hintText: hint),
          ),
        ],
      ),
    );
  }
}

// ── Alert banner ────────────────────────────────────────────────────────────
class AlertBanner extends StatelessWidget {
  final String message;
  final bool error;
  const AlertBanner({super.key, required this.message, this.error = true});

  @override
  Widget build(BuildContext context) {
    final color = error ? AppColors.danger : AppColors.sky;
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(message, style: TextStyle(color: color, fontSize: 14, height: 1.4)),
    );
  }
}

// ── Empty state ─────────────────────────────────────────────────────────────
class EmptyState extends StatelessWidget {
  final String icon;
  final String title;
  final String body;
  final Widget? action;
  const EmptyState({super.key, required this.icon, required this.title, required this.body, this.action});

  @override
  Widget build(BuildContext context) {
    return ACard(
      padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 20),
      child: Column(
        children: [
          Text(icon, style: const TextStyle(fontSize: 40)),
          const SizedBox(height: 16),
          Text(title, style: const TextStyle(color: AppColors.cream, fontSize: 17, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Text(body, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.creamDim, fontSize: 14, height: 1.4)),
          if (action != null) ...[const SizedBox(height: 20), action!],
        ],
      ),
    );
  }
}

// ── Avatar ──────────────────────────────────────────────────────────────────
class Avatar extends StatelessWidget {
  final String? name;
  final double size;
  const Avatar({super.key, this.name, this.size = 40});

  @override
  Widget build(BuildContext context) {
    final initial = ((name ?? '?').isEmpty ? '?' : (name ?? '?')[0]).toUpperCase();
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: const BoxDecoration(color: AppColors.terraDim, shape: BoxShape.circle),
      child: Text(
        initial,
        style: TextStyle(color: AppColors.terraLight, fontSize: size * 0.4, fontWeight: FontWeight.w600),
      ),
    );
  }
}

// ── Loading full-screen ─────────────────────────────────────────────────────
class LoadingScreen extends StatelessWidget {
  const LoadingScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: AppColors.midnight,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Ritha', style: TextStyle(color: AppColors.cream, fontSize: 28, fontWeight: FontWeight.w700)),
            SizedBox(height: 20),
            CircularProgressIndicator(color: AppColors.terra),
          ],
        ),
      ),
    );
  }
}

// ── Toast ───────────────────────────────────────────────────────────────────
class AppToast {
  static void show(BuildContext context, String message, {bool error = false}) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Row(children: [
            Text(error ? '⚠' : '✓', style: const TextStyle(fontSize: 14)),
            const SizedBox(width: 8),
            Expanded(child: Text(message, style: const TextStyle(color: AppColors.cream, fontSize: 13))),
          ]),
          backgroundColor: error ? const Color(0xCC2A1618) : AppColors.surface2,
          behavior: SnackBarBehavior.floating,
          duration: const Duration(seconds: 3),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          margin: const EdgeInsets.all(12),
        ),
      );
  }
}

// ── Primary button (loading-aware) ──────────────────────────────────────────
class APrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool loading;
  final IconData? icon;
  const APrimaryButton({super.key, required this.label, this.onPressed, this.loading = false, this.icon});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: loading ? null : onPressed,
        child: loading
            ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (icon != null) ...[Icon(icon, size: 16), const SizedBox(width: 8)],
                  Text(label),
                ],
              ),
      ),
    );
  }
}
