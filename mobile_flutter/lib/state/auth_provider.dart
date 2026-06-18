import 'package:flutter/foundation.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import '../api/api.dart';
import '../api/api_client.dart';

class AuthProvider extends ChangeNotifier {
  Map<String, dynamic>? _user;
  bool _loading = true;

  Map<String, dynamic>? get user => _user;
  bool get loading => _loading;
  bool get isAuthenticated => _user != null;

  // Attach/clear the Sentry user from the current _user. No-op when Sentry
  // isn't initialised (no DSN), so it's safe to call unconditionally.
  void _syncSentryUser() {
    Sentry.configureScope((scope) {
      scope.setUser(
        _user == null
            ? null
            : SentryUser(
                id: _user!['id']?.toString(),
                email: _user!['email'] as String?,
              ),
      );
    });
  }

  AuthProvider() {
    ApiClient.instance.setOnAuthFailure(() async {
      _user = null;
      _syncSentryUser();
      notifyListeners();
      return null;
    });
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    final token = await ApiClient.instance.getAccessToken();
    if (token == null) {
      _loading = false;
      notifyListeners();
      return;
    }
    try {
      final me = await authApi.me() as Map<String, dynamic>;
      _user = me;
    } catch (_) {
      await ApiClient.instance.clearTokens();
      _user = null;
    } finally {
      _loading = false;
      _syncSentryUser();
      notifyListeners();
    }
  }

  Future<void> login(String email, String password) async {
    final data =
        await authApi.login({'email': email, 'password': password})
            as Map<String, dynamic>;
    await ApiClient.instance.setTokens(
      data['access'] as String,
      data['refresh'] as String,
    );
    final me = await authApi.me() as Map<String, dynamic>;
    _user = me;
    _syncSentryUser();
    notifyListeners();
  }

  Future<void> register(String email, String password, String firstName) async {
    await authApi.register({
      'email': email,
      'password': password,
      'first_name': firstName,
    });
  }

  Future<void> logout() async {
    final refresh = await ApiClient.instance.getRefreshToken();
    if (refresh != null) {
      try {
        await authApi.logout(refresh);
      } catch (_) {}
    }
    await ApiClient.instance.clearTokens();
    _user = null;
    _syncSentryUser();
    notifyListeners();
  }

  Future<void> forgotPassword(String email) async {
    await authApi.forgotPassword({'email': email});
  }

  Future<void> resetPassword(
    String token,
    String email,
    String password,
  ) async {
    await authApi.resetPassword({
      'token': token,
      'email': email,
      'new_password': password,
    });
  }

  Future<void> verifyEmail(String token, String email) async {
    await authApi.verifyEmail({'token': token, 'email': email});
  }

  Future<void> resendVerification(String email) async {
    await authApi.resendVerification({'email': email});
  }

  Future<void> reloadUser() async {
    try {
      _user = await authApi.me() as Map<String, dynamic>;
      notifyListeners();
    } catch (_) {}
  }

  void updateLocalUser(Map<String, dynamic> patch) {
    if (_user == null) return;
    _user = {..._user!, ...patch};
    notifyListeners();
  }
}
