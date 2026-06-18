import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../state/auth_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';
import '../api/api_client.dart';

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
