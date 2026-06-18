import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:provider/provider.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'firebase_options.dart';
import 'services/push_notification_service.dart';
import 'state/auth_provider.dart';
import 'theme/app_theme.dart';
import 'router.dart';

// Set in CI/release builds: flutter build --dart-define=SENTRY_DSN=...
// Empty by default, so local/dev runs send nothing.
const String _sentryDsn = String.fromEnvironment(
  'SENTRY_DSN',
  defaultValue: '',
);
const String _sentryEnv = String.fromEnvironment(
  'SENTRY_ENVIRONMENT',
  defaultValue: 'production',
);
const String _appVersion = String.fromEnvironment(
  'APP_VERSION',
  defaultValue: '',
);

Future<void> _bootstrap() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  await PushNotificationService.instance.init();
  await loadOnboardingSkipFlag();
  runApp(const RithaApp());
}

Future<void> main() async {
  if (_sentryDsn.isEmpty) {
    await _bootstrap();
    return;
  }
  await SentryFlutter.init((options) {
    options.dsn = _sentryDsn;
    options.environment = _sentryEnv;
    if (_appVersion.isNotEmpty) options.release = _appVersion;
    options.tracesSampleRate = 0.1;
    options.sendDefaultPii = false;
  }, appRunner: _bootstrap);
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
