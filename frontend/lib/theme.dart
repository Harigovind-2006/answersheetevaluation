import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

const Color primaryBlue = Color(0xFF0C51C3);
const Color backgroundLight = Color(0xFFF7F8FC);
const Color textDark = Color(0xFF1E293B);
const Color textMuted = Color(0xFF64748B);
const Color surfaceWhite = Colors.white;

ThemeData appTheme() {
  return ThemeData(
    scaffoldBackgroundColor: backgroundLight,
    primaryColor: primaryBlue,
    colorScheme: ColorScheme.fromSeed(
      seedColor: primaryBlue,
      primary: primaryBlue,
      surface: surfaceWhite,
    ),
    textTheme: GoogleFonts.interTextTheme().apply(
      bodyColor: textDark,
      displayColor: textDark,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: backgroundLight,
      elevation: 0,
      iconTheme: IconThemeData(color: primaryBlue),
      titleTextStyle: TextStyle(
        color: primaryBlue,
        fontSize: 20,
        fontWeight: FontWeight.w600,
      ),
      centerTitle: false,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: primaryBlue,
        foregroundColor: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        padding: const EdgeInsets.symmetric(vertical: 16),
        textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
      ),
    ),
  );
}
