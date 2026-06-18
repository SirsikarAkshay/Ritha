import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../state/auth_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';
import '../api/api_client.dart';

class VerifyEmailScreen extends StatefulWidget {
  final String email;
  const VerifyEmailScreen({super.key, required this.email});
  @override
  State<VerifyEmailScreen> createState() => _VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends State<VerifyEmailScreen> {
  late final TextEditingController _email;
  final _token = TextEditingController();
  bool _loading = false;
  bool _resending = false;
  String? _error;
  String? _message;

  @override
  void initState() {
    super.initState();
    _email = TextEditingController(text: widget.email);
  }

  @override
  void dispose() {
    _email.dispose();
    _token.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _error = null;
      _message = null;
      _loading = true;
    });
    try {
      await context.read<AuthProvider>().verifyEmail(
        _token.text.trim(),
        _email.text.trim(),
      );
      setState(() => _message = 'Email verified! Redirecting to login…');
      await Future.delayed(const Duration(milliseconds: 1200));
      if (mounted) context.go('/login');
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _resend() async {
    if (_email.text.trim().isEmpty) {
      setState(() => _error = 'Enter your email first.');
      return;
    }
    setState(() {
      _resending = true;
      _error = null;
    });
    try {
      await context.read<AuthProvider>().resendVerification(_email.text.trim());
      setState(() => _message = 'A new verification link has been sent.');
    } catch (_) {
      setState(() => _error = 'Failed to resend. Try again later.');
    } finally {
      if (mounted) setState(() => _resending = false);
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
                  const Text(
                    'Verify your email',
                    style: TextStyle(
                      color: AppColors.cream,
                      fontSize: 24,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Check your inbox for a verification link. Open the link or paste the code below.',
                    style: TextStyle(color: AppColors.creamDim, fontSize: 14),
                  ),
                  const SizedBox(height: 22),
                  if (_error != null) AlertBanner(message: _error!),
                  if (_message != null)
                    AlertBanner(message: _message!, error: false),
                  LabeledInput(
                    label: 'Email',
                    controller: _email,
                    keyboardType: TextInputType.emailAddress,
                  ),
                  LabeledInput(
                    label: 'Verification code',
                    controller: _token,
                    hint: 'Paste the code from the email',
                  ),
                  APrimaryButton(
                    label: 'Verify email',
                    loading: _loading,
                    onPressed: _submit,
                  ),
                  TextButton(
                    onPressed: _resending ? null : _resend,
                    child: Text(
                      _resending ? 'Sending…' : 'Resend verification email',
                    ),
                  ),
                  TextButton(
                    onPressed: () => context.go('/login'),
                    child: const Text('Back to login'),
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
