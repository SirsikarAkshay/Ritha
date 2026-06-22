import 'dart:async';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import '../api/api.dart';

const _vapidKey =
    'BOVW5On13xvLTVhNiN1eciAX77ipfinAQqMZJWwUT3mHv6pzOTbumJGuw-J_wvhU7ZVbq96Cdxcas2VZgcmv4bo';

@pragma('vm:entry-point')
Future<void> _firebaseBackgroundHandler(RemoteMessage message) async {
  debugPrint('FCM background message: ${message.messageId}');
}

class PushNotificationService {
  PushNotificationService._();
  static final instance = PushNotificationService._();

  FirebaseMessaging? _messagingInstance;
  String? _token;
  bool _initialized = false;

  String? get token => _token;

  /// Lazily resolves [FirebaseMessaging], returning null when Firebase isn't
  /// configured/initialized for this build so every caller degrades gracefully
  /// instead of throwing.
  FirebaseMessaging? get _messaging {
    try {
      return _messagingInstance ??= FirebaseMessaging.instance;
    } catch (_) {
      return null;
    }
  }

  Future<void> init() async {
    if (_initialized) return;
    final messaging = _messaging;
    if (messaging == null) {
      debugPrint('Push notifications unavailable: Firebase not configured.');
      return;
    }
    _initialized = true;

    if (!kIsWeb) {
      FirebaseMessaging.onBackgroundMessage(_firebaseBackgroundHandler);
    }

    FirebaseMessaging.onMessage.listen((message) {
      debugPrint('FCM foreground: ${message.notification?.title}');
    });

    FirebaseMessaging.onMessageOpenedApp.listen((message) {
      debugPrint('FCM tap: ${message.data}');
    });

    if (!kIsWeb) {
      final initial = await messaging.getInitialMessage();
      if (initial != null) {
        debugPrint('FCM launched from: ${initial.data}');
      }
    }

    messaging.onTokenRefresh.listen((newToken) {
      _token = newToken;
      _sendTokenToBackend(newToken, enabled: true);
    });
  }

  Future<bool> requestPermissionAndRegister() async {
    final messaging = _messaging;
    if (messaging == null) return false;
    final settings = await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional) {
      _token = await messaging.getToken(vapidKey: kIsWeb ? _vapidKey : null);
      if (_token != null) {
        await _sendTokenToBackend(_token!, enabled: true);
      }
      return true;
    }
    return false;
  }

  Future<void> disable() async {
    await _sendTokenToBackend('', enabled: false);
    await _messaging?.deleteToken();
    _token = null;
  }

  Future<void> _sendTokenToBackend(
    String token, {
    required bool enabled,
  }) async {
    try {
      await authApi.registerPushToken(token, enabled);
    } catch (e) {
      debugPrint('Failed to send push token: $e');
    }
  }
}
