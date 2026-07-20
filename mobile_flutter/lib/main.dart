import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:provider/provider.dart';
import 'firebase_options.dart';
import 'services/push_notification_service.dart';
import 'state/auth_provider.dart';
import 'theme/app_theme.dart';
import 'router.dart';

Future<void> _bootstrap() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Firebase powers push notifications only. If it hasn't been configured for
  // this build (no firebase_options / google-services files yet), skip it so
  // the app still launches instead of crashing — push is simply unavailable
  // until `flutterfire configure` has been run.
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
    await PushNotificationService.instance.init();
  } catch (e) {
    debugPrint(
      'Firebase/push notifications unavailable, continuing without: $e',
    );
  }
  await loadOnboardingSkipFlag();
  runApp(const RithaApp());
}

Future<void> main() async {
  // Error monitoring (Sentry) was removed to unblock the Android build — the
  // sentry_flutter Kotlin didn't compile against Kotlin 2.2.x. Re-add a
  // compatible sentry_flutter and wrap _bootstrap() in SentryFlutter.init when
  // wiring production observability back up.
  await _bootstrap();
}

class RithaApp extends StatelessWidget {
  const RithaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AuthProvider(),
      child: Builder(
        builder: (context) {
          final router = buildRouter(context.read<AuthProvider>());
          return MaterialApp.router(
            title: 'Ritha',
            theme: buildAppTheme(),
            debugShowCheckedModeBanner: false,
            routerConfig: router,
          );
        },
      ),
    );
  }
}
