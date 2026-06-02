import 'package:flutter/material.dart';

class AppColors {
  static const midnight   = Color(0xFF0D0F14);
  static const cream      = Color(0xFFF5F0E8);
  static const creamDim   = Color(0x8CF5F0E8);
  static const creamLight = Color(0x14F5F0E8);
  static const terra      = Color(0xFFD4724A);
  static const terraLight = Color(0xFFE8956E);
  static const terraDim   = Color(0x1FD4724A);
  static const sky        = Color(0xFF6FA8C7);
  static const sage       = Color(0xFF7BA67E);
  static const sageDim    = Color(0x1F7BA67E);
  static const gold       = Color(0xFFC9A84C);
  static const goldDim    = Color(0x1FC9A84C);
  static const surface1   = Color(0xFF161921);
  static const surface2   = Color(0xFF1C1F29);
  static const surface3   = Color(0xFF252833);
  static const border     = Color(0x14F5F0E8);
  static const danger     = Color(0xFFF87171);
}

ThemeData buildAppTheme() {
  const base = ColorScheme.dark(
    primary: AppColors.terra,
    secondary: AppColors.terraLight,
    surface: AppColors.surface1,
    onSurface: AppColors.cream,
    error: AppColors.danger,
  );

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: base,
    scaffoldBackgroundColor: AppColors.midnight,
    fontFamily: 'System',
    textTheme: const TextTheme(
      displayLarge: TextStyle(color: AppColors.cream, fontWeight: FontWeight.w700),
      displayMedium: TextStyle(color: AppColors.cream, fontWeight: FontWeight.w700),
      headlineLarge: TextStyle(color: AppColors.cream, fontWeight: FontWeight.w700),
      headlineMedium: TextStyle(color: AppColors.cream, fontWeight: FontWeight.w700),
      titleLarge: TextStyle(color: AppColors.cream, fontWeight: FontWeight.w600),
      titleMedium: TextStyle(color: AppColors.cream, fontWeight: FontWeight.w600),
      bodyLarge: TextStyle(color: AppColors.cream),
      bodyMedium: TextStyle(color: AppColors.cream),
      labelLarge: TextStyle(color: AppColors.cream),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface2,
      hintStyle: const TextStyle(color: AppColors.creamDim),
      labelStyle: const TextStyle(color: AppColors.creamDim),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.terra),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.terra,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.cream,
        side: const BorderSide(color: AppColors.border),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: AppColors.terraLight),
    ),
    dividerColor: AppColors.border,
    cardColor: AppColors.surface1,
  );
}
