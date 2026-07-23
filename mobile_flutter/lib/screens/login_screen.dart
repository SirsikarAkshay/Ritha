import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';
import '../state/auth_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';
import '../api/api_client.dart';

// Build-time config (pass via --dart-define). Buttons render only when set.
// GOOGLE_SERVER_CLIENT_ID is the *web* OAuth client id — passing it as
// google_sign_in's serverClientId makes the returned ID token's audience equal
// it, which the backend allowlist accepts.
const _googleServerClientId = String.fromEnvironment('GOOGLE_SERVER_CLIENT_ID');
const _appleServicesId = String.fromEnvironment('APPLE_SERVICES_ID');
const _appleRedirectUri = String.fromEnvironment('APPLE_REDIRECT_URI');

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _firstName = TextEditingController();
  bool _register = false;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _firstName.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final auth = context.read<AuthProvider>();
    try {
      if (_register) {
        await auth.register(
          _email.text.trim(),
          _password.text,
          _firstName.text.trim(),
        );
        if (!mounted) return;
        context.go(
          '/verify-email?email=${Uri.encodeQueryComponent(_email.text.trim())}',
        );
      } else {
        await auth.login(_email.text.trim(), _password.text);
      }
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = 'Something went wrong. Try again.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _googleSignIn() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final gsi = GoogleSignIn(
        serverClientId: _googleServerClientId,
        scopes: const ['email'],
      );
      final account = await gsi.signIn();
      if (account == null) {
        // User cancelled the picker.
        if (mounted) setState(() => _loading = false);
        return;
      }
      final gauth = await account.authentication;
      final idToken = gauth.idToken;
      if (idToken == null) throw Exception('no-id-token');
      if (!mounted) return;
      await context.read<AuthProvider>().loginWithGoogle(idToken);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'Google sign-in failed. Please try again.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _appleSignIn() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final cred = await SignInWithApple.getAppleIDCredential(
        scopes: const [
          AppleIDAuthorizationScopes.email,
          AppleIDAuthorizationScopes.fullName,
        ],
        // Android has no native Apple flow — it uses the web flow, which needs
        // the Services ID + return URL. Harmless (unused) on iOS.
        webAuthenticationOptions: _appleServicesId.isEmpty
            ? null
            : WebAuthenticationOptions(
                clientId: _appleServicesId,
                redirectUri: Uri.parse(_appleRedirectUri),
              ),
      );
      final idToken = cred.identityToken;
      if (idToken == null) throw Exception('no-id-token');
      if (!mounted) return;
      await context.read<AuthProvider>().loginWithApple(
        idToken,
        firstName: cred.givenName ?? '',
        lastName: cred.familyName ?? '',
      );
    } on SignInWithAppleAuthorizationException catch (e) {
      // Swallow user-cancellations; surface anything else.
      if (e.code != AuthorizationErrorCode.canceled) {
        setState(() => _error = 'Apple sign-in failed. Please try again.');
      }
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'Apple sign-in failed. Please try again.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.midnight,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 24),
                  const Text(
                    'Ritha',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: AppColors.cream,
                      fontSize: 32,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'YOUR WARDROBE ASSISTANT',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: AppColors.terra,
                      fontSize: 11,
                      letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 36),
                  Text(
                    _register ? 'Create account' : 'Welcome back',
                    style: const TextStyle(
                      color: AppColors.cream,
                      fontSize: 24,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _register
                        ? 'Start your AI-powered wardrobe journey.'
                        : 'Sign in to your style companion.',
                    style: const TextStyle(
                      color: AppColors.creamDim,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 22),
                  if (_error != null) AlertBanner(message: _error!),
                  if (_register)
                    LabeledInput(
                      label: 'First name',
                      controller: _firstName,
                      hint: 'Jane',
                    ),
                  LabeledInput(
                    label: 'Email',
                    controller: _email,
                    hint: 'you@example.com',
                    keyboardType: TextInputType.emailAddress,
                  ),
                  LabeledInput(
                    label: 'Password',
                    controller: _password,
                    obscure: true,
                    hint: _register ? 'Min. 8 characters' : '••••••••',
                  ),
                  const SizedBox(height: 6),
                  APrimaryButton(
                    label: _register ? 'Create account' : 'Sign in',
                    loading: _loading,
                    onPressed: _submit,
                  ),
                  if (_googleServerClientId.isNotEmpty ||
                      _appleServicesId.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        const Expanded(
                          child: Divider(color: AppColors.creamDim),
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                          child: Text(
                            'or',
                            style: TextStyle(
                              color: AppColors.creamDim,
                              fontSize: 12,
                            ),
                          ),
                        ),
                        const Expanded(
                          child: Divider(color: AppColors.creamDim),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    if (_googleServerClientId.isNotEmpty)
                      _SocialButton(
                        label: 'Continue with Google',
                        background: Colors.white,
                        foreground: Colors.black87,
                        onPressed: _loading ? null : _googleSignIn,
                      ),
                    if (_appleServicesId.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      _SocialButton(
                        label: 'Continue with Apple',
                        background: Colors.black,
                        foreground: Colors.white,
                        onPressed: _loading ? null : _appleSignIn,
                      ),
                    ],
                  ],
                  if (!_register)
                    TextButton(
                      onPressed: () => context.go('/forgot-password'),
                      child: const Text('Forgot password?'),
                    ),
                  const SizedBox(height: 6),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        _register
                            ? 'Already have an account?'
                            : "Don't have an account?",
                        style: const TextStyle(
                          color: AppColors.creamDim,
                          fontSize: 14,
                        ),
                      ),
                      TextButton(
                        onPressed: () => setState(() {
                          _register = !_register;
                          _error = null;
                        }),
                        child: Text(_register ? 'Sign in' : 'Sign up'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SocialButton extends StatelessWidget {
  final String label;
  final Color background;
  final Color foreground;
  final VoidCallback? onPressed;
  const _SocialButton({
    required this.label,
    required this.background,
    required this.foreground,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      child: ElevatedButton(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: background,
          foregroundColor: foreground,
          disabledBackgroundColor: background.withValues(alpha: 0.5),
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(100),
          ),
        ),
        child: Text(
          label,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}
