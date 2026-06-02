import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../state/auth_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';
import '../api/api_client.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});
  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _email = TextEditingController();
  bool _loading = false;
  bool _sent = false;
  String? _error;

  @override
  void dispose() { _email.dispose(); super.dispose(); }

  Future<void> _submit() async {
    setState(() { _loading = true; _error = null; });
    try {
      await context.read<AuthProvider>().forgotPassword(_email.text.trim());
      setState(() => _sent = true);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
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
                  const Text('Reset password', style: TextStyle(color: AppColors.cream, fontSize: 24, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  const Text("Enter your email and we'll send you a reset link.",
                      style: TextStyle(color: AppColors.creamDim, fontSize: 14)),
                  const SizedBox(height: 22),
                  if (_error != null) AlertBanner(message: _error!),
                  if (_sent) const AlertBanner(message: 'Check your inbox for a password reset link.', error: false),
                  LabeledInput(label: 'Email', controller: _email, hint: 'you@example.com', keyboardType: TextInputType.emailAddress),
                  APrimaryButton(
                    label: 'Send reset link',
                    loading: _loading,
                    onPressed: _sent ? null : _submit,
                  ),
                  if (_sent) ...[
                    const SizedBox(height: 12),
                    OutlinedButton(
                      onPressed: () => context.go('/reset-password?email=${Uri.encodeQueryComponent(_email.text.trim())}'),
                      child: const Text('Enter reset code'),
                    ),
                  ],
                  const SizedBox(height: 8),
                  TextButton(onPressed: () => context.go('/login'), child: const Text('Back to login')),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
