import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../state/auth_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';
import '../api/api_client.dart';

class ResetPasswordScreen extends StatefulWidget {
  final String email;
  const ResetPasswordScreen({super.key, required this.email});
  @override
  State<ResetPasswordScreen> createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends State<ResetPasswordScreen> {
  late final TextEditingController _email;
  final _token   = TextEditingController();
  final _pass    = TextEditingController();
  final _confirm = TextEditingController();
  bool _loading = false;
  String? _error;
  String? _message;

  @override
  void initState() {
    super.initState();
    _email = TextEditingController(text: widget.email);
  }

  @override
  void dispose() {
    _email.dispose(); _token.dispose(); _pass.dispose(); _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() { _error = null; _message = null; });
    if (_pass.text.length < 8) { setState(() => _error = 'Password must be at least 8 characters.'); return; }
    if (_pass.text != _confirm.text) { setState(() => _error = 'Passwords do not match.'); return; }
    setState(() => _loading = true);
    try {
      await context.read<AuthProvider>().resetPassword(_token.text.trim(), _email.text.trim(), _pass.text);
      setState(() => _message = 'Password reset. Redirecting to login…');
      await Future.delayed(const Duration(milliseconds: 1200));
      if (mounted) context.go('/login');
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
                  const Text('Set new password', style: TextStyle(color: AppColors.cream, fontSize: 24, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  const Text('Enter the code we emailed you and choose a new password.',
                      style: TextStyle(color: AppColors.creamDim, fontSize: 14)),
                  const SizedBox(height: 22),
                  if (_error != null) AlertBanner(message: _error!),
                  if (_message != null) AlertBanner(message: _message!, error: false),
                  LabeledInput(label: 'Email', controller: _email, keyboardType: TextInputType.emailAddress),
                  LabeledInput(label: 'Reset code', controller: _token, hint: 'Paste the code from the email'),
                  LabeledInput(label: 'New password', controller: _pass, obscure: true, hint: 'Min. 8 characters'),
                  LabeledInput(label: 'Confirm password', controller: _confirm, obscure: true),
                  APrimaryButton(label: 'Reset password', loading: _loading, onPressed: _submit),
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
