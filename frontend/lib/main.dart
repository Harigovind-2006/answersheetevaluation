import 'package:flutter/material.dart';

import 'package:go_router/go_router.dart';

import 'theme.dart';
import 'screens/login_screen.dart';
import 'screens/main_screen.dart';
import 'screens/camera_screen.dart';
import 'screens/register_screen.dart';

void main() {
  runApp(const MyApp());
}

final _router = GoRouter(
  initialLocation: '/login',
  routes: [
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: '/register',
      builder: (context, state) => const RegisterScreen(),
    ),
    GoRoute(
      path: '/main',
      builder: (context, state) {
        final extra = state.extra as Map<String, dynamic>?;
        return MainScreen(initialData: extra);
      },
    ),
    GoRoute(
      path: '/camera',
      builder: (context, state) => const CameraScreen(),
    ),
  ],
);

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Correction Dashboard',
      theme: appTheme(),
      routerConfig: _router,
      debugShowCheckedModeBanner: false,
    );
  }
}
