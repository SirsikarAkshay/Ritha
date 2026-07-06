import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'state/auth_provider.dart';
import 'screens/login_screen.dart';
import 'screens/forgot_password_screen.dart';
import 'screens/reset_password_screen.dart';
import 'screens/verify_email_screen.dart';
import 'screens/home_shell.dart';
import 'screens/dashboard_screen.dart';
import 'screens/wardrobe_screen.dart';
import 'screens/itinerary_screen.dart';
import 'screens/trip_planner_screen.dart';
import 'screens/packing_capacity_screen.dart';
import 'screens/cultural_screen.dart';
import 'screens/sustainability_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/people_screen.dart';
import 'screens/messages_screen.dart';
import 'screens/shared_wardrobes_screen.dart';
import 'screens/shared_wardrobe_detail_screen.dart';
import 'screens/outfit_history_screen.dart';
import 'screens/onboarding_screen.dart';
import 'widgets/ui.dart';

import 'package:shared_preferences/shared_preferences.dart';

// Local-only flag mirroring the web client's localStorage key. Set when the user
// taps "Skip — I'll add manually" so we don't loop them back to /onboarding on
// every navigation. Cleared if they later finish onboarding (server flag wins).
bool _onboardingSkipped = false;
Future<void> loadOnboardingSkipFlag() async {
  final prefs = await SharedPreferences.getInstance();
  _onboardingSkipped = prefs.getBool('ritha_onboarding_skipped') ?? false;
}

Future<void> setOnboardingSkipped(bool v) async {
  _onboardingSkipped = v;
  final prefs = await SharedPreferences.getInstance();
  await prefs.setBool('ritha_onboarding_skipped', v);
}

GoRouter buildRouter(AuthProvider auth) {
  return GoRouter(
    refreshListenable: auth,
    initialLocation: '/',
    redirect: (context, state) {
      if (auth.loading) return null;
      final signedIn = auth.isAuthenticated;
      final loc = state.matchedLocation;
      final isAuthRoute =
          loc == '/login' ||
          loc == '/forgot-password' ||
          loc == '/reset-password' ||
          loc == '/verify-email';
      if (!signedIn && !isAuthRoute) return '/login';
      if (signedIn && isAuthRoute) return '/';

      // First-time users → /onboarding, unless they've explicitly skipped or
      // are already on the onboarding screen.
      if (signedIn && !isAuthRoute && loc != '/onboarding') {
        final completed = auth.user?['has_completed_onboarding'] == true;
        if (!completed && !_onboardingSkipped) return '/onboarding';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(
        path: '/forgot-password',
        builder: (_, __) => const ForgotPasswordScreen(),
      ),
      GoRoute(
        path: '/reset-password',
        builder: (ctx, st) =>
            ResetPasswordScreen(email: st.uri.queryParameters['email'] ?? ''),
      ),
      GoRoute(
        path: '/verify-email',
        builder: (ctx, st) =>
            VerifyEmailScreen(email: st.uri.queryParameters['email'] ?? ''),
      ),
      GoRoute(
        path: '/onboarding',
        builder: (_, __) => const OnboardingScreen(),
      ),
      ShellRoute(
        builder: (ctx, state, child) => HomeShell(child: child),
        routes: [
          GoRoute(path: '/', builder: (_, __) => const DashboardScreen()),
          GoRoute(
            path: '/wardrobe',
            builder: (_, __) => const WardrobeScreen(),
          ),
          GoRoute(
            path: '/itinerary',
            builder: (_, __) => const ItineraryScreen(),
          ),
          GoRoute(
            path: '/trips',
            builder: (_, __) => const TripPlannerScreen(),
          ),
          GoRoute(
            path: '/packing',
            builder: (_, __) => const PackingCapacityScreen(),
          ),
          GoRoute(
            path: '/cultural',
            builder: (_, __) => const CulturalScreen(),
          ),
          GoRoute(
            path: '/sustainability',
            builder: (_, __) => const SustainabilityScreen(),
          ),
          GoRoute(
            path: '/outfit-history',
            builder: (_, __) => const OutfitHistoryScreen(),
          ),
          GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
          GoRoute(path: '/people', builder: (_, __) => const PeopleScreen()),
          GoRoute(
            path: '/messages',
            builder: (ctx, st) {
              final openWith = int.tryParse(
                st.uri.queryParameters['open_user_id'] ?? '',
              );
              return MessagesScreen(openWithUserId: openWith);
            },
          ),
          GoRoute(
            path: '/shared-wardrobes',
            builder: (_, __) => const SharedWardrobesScreen(),
          ),
          GoRoute(
            path: '/shared-wardrobes/:id',
            builder: (ctx, st) => SharedWardrobeDetailScreen(
              id: int.parse(st.pathParameters['id']!),
            ),
          ),
        ],
      ),
    ],
    errorBuilder: (ctx, st) => const Scaffold(body: LoadingScreen()),
  );
}
