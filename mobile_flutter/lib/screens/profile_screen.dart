import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/api.dart';
import '../services/device_calendar_service.dart';
import '../services/push_notification_service.dart';
import '../state/auth_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

const _timezones = [
  'UTC',
  'Europe/Zurich',
  'Europe/London',
  'America/New_York',
  'America/Los_Angeles',
  'Asia/Tokyo',
  'Asia/Singapore',
  'Australia/Sydney',
];

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});
  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _currentPw = TextEditingController();
  final _newPw = TextEditingController();
  String _tz = 'UTC';

  bool _saving = false;
  bool _changingPw = false;
  String? _message;
  bool _isError = false;

  Map<String, dynamic>? _calStatus;
  String? _busyProvider;
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    final user = context.read<AuthProvider>().user ?? {};
    _firstName.text = user['first_name'] ?? '';
    _lastName.text = user['last_name'] ?? '';
    _tz = user['timezone'] ?? 'UTC';
    _refreshCalStatus();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _firstName.dispose();
    _lastName.dispose();
    _currentPw.dispose();
    _newPw.dispose();
    super.dispose();
  }

  Future<void> _refreshCalStatus() async {
    try {
      final s = await calendarApi.status();
      if (!mounted) return;
      setState(
        () => _calStatus = s is Map ? Map<String, dynamic>.from(s) : null,
      );
    } catch (_) {}
  }

  void _flash(String msg, {bool error = false}) {
    setState(() {
      _message = msg;
      _isError = error;
    });
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) setState(() => _message = null);
    });
  }

  Future<void> _saveProfile() async {
    setState(() => _saving = true);
    try {
      final updated =
          await authApi.updateMe({
                'first_name': _firstName.text.trim(),
                'last_name': _lastName.text.trim(),
                'timezone': _tz,
              })
              as Map;
      if (!mounted) return;
      context.read<AuthProvider>().updateLocalUser(
        Map<String, dynamic>.from(updated),
      );
      _flash('Profile updated.');
    } catch (e) {
      _flash(e.toString(), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _changePassword() async {
    if (_newPw.text.length < 8) {
      _flash('New password must be at least 8 characters.', error: true);
      return;
    }
    setState(() => _changingPw = true);
    try {
      await authApi.changePassword({
        'current_password': _currentPw.text,
        'new_password': _newPw.text,
      });
      _currentPw.clear();
      _newPw.clear();
      _flash('Password changed successfully.');
    } catch (e) {
      _flash(e.toString(), error: true);
    } finally {
      if (mounted) setState(() => _changingPw = false);
    }
  }

  // ── OAuth connect (Google / Outlook) ─────────────────────────────────────

  Future<void> _connectOAuth(String provider) async {
    setState(() => _busyProvider = provider);
    try {
      final res =
          await (provider == 'google'
                  ? calendarApi.google.connect()
                  : calendarApi.outlook.connect())
              as Map;
      final authUrl = res['auth_url']?.toString();
      if (authUrl == null || authUrl.isEmpty) {
        _flash('$provider connect URL missing.', error: true);
        return;
      }
      final uri = Uri.parse(authUrl);
      await launchUrl(uri, mode: LaunchMode.externalApplication);
      _startPolling(provider);
      if (!mounted) return;
      _flash(
        'Complete the $provider sign-in in your browser. We\'ll detect the connection automatically.',
      );
    } catch (e) {
      final msg = e.toString();
      if (msg.contains('not_configured')) {
        _flash(
          '$provider requires backend client-id/secret configuration.',
          error: true,
        );
      } else {
        _flash('Failed to start $provider connection.', error: true);
      }
    } finally {
      if (mounted) setState(() => _busyProvider = null);
    }
  }

  void _startPolling(String provider) {
    _pollTimer?.cancel();
    final started = DateTime.now();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (t) async {
      if (!mounted ||
          DateTime.now().difference(started) > const Duration(minutes: 2)) {
        t.cancel();
        return;
      }
      try {
        final s = await calendarApi.status();
        if (!mounted) return;
        if (s is Map &&
            s[provider] is Map &&
            (s[provider]['connected'] == true)) {
          t.cancel();
          setState(() => _calStatus = Map<String, dynamic>.from(s));
          _flash('${_providerLabel(provider)} connected!');
        }
      } catch (_) {}
    });
  }

  // ── Apple connect (credential sheet — fallback for web) ─────────────────

  Future<void> _connectApple() async {
    final creds = await showModalBottomSheet<Map<String, String>>(
      context: context,
      backgroundColor: AppColors.surface1,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => const _AppleCredentialSheet(),
    );
    if (creds == null) return;

    setState(() => _busyProvider = 'apple');
    try {
      await calendarApi.apple.connect(creds);
      await _refreshCalStatus();
      _flash('Apple Calendar connected!');
    } catch (e) {
      _flash('Failed to connect Apple Calendar: $e', error: true);
    } finally {
      if (mounted) setState(() => _busyProvider = null);
    }
  }

  // ── Device calendar (native EventKit / CalendarProvider) ───────────────

  bool _deviceSyncing = false;
  int? _deviceEventCount;

  Future<void> _syncDeviceCalendar() async {
    setState(() => _deviceSyncing = true);
    try {
      final result = await DeviceCalendarService.instance.syncToBackend();
      if (!mounted) return;
      if (result.containsKey('error')) {
        _flash(result['error'].toString(), error: true);
      } else {
        final total =
            result['total'] ??
            (result['created'] ?? 0) + (result['updated'] ?? 0);
        final cals = result['calendars'] ?? 0;
        setState(() => _deviceEventCount = total is int ? total : 0);
        _flash('Synced $total events from $cals calendars');
      }
    } catch (e) {
      _flash('Calendar sync failed: $e', error: true);
    } finally {
      if (mounted) setState(() => _deviceSyncing = false);
    }
  }

  // ── Disconnect / Sync ────────────────────────────────────────────────────

  Future<void> _disconnect(String provider) async {
    final ok = await _confirm('Disconnect ${_providerLabel(provider)}?');
    if (ok != true) return;
    try {
      switch (provider) {
        case 'google':
          await calendarApi.google.disconnect();
          break;
        case 'apple':
          await calendarApi.apple.disconnect();
          break;
        case 'outlook':
          await calendarApi.outlook.disconnect();
          break;
      }
      await _refreshCalStatus();
      _flash('${_providerLabel(provider)} disconnected.');
    } catch (e) {
      _flash('Failed to disconnect: $e', error: true);
    }
  }

  Future<void> _sync(String provider) async {
    setState(() => _busyProvider = provider);
    try {
      switch (provider) {
        case 'google':
          await calendarApi.google.sync();
          break;
        case 'apple':
          await calendarApi.apple.sync();
          break;
        case 'outlook':
          await calendarApi.outlook.sync();
          break;
      }
      await _refreshCalStatus();
      _flash('${_providerLabel(provider)} synced!');
    } catch (e) {
      _flash('Sync failed: $e', error: true);
    } finally {
      if (mounted) setState(() => _busyProvider = null);
    }
  }

  // ── Danger zone ──────────────────────────────────────────────────────────

  Future<void> _deleteAccount() async {
    final ok = await _confirm(
      'Delete your account?',
      body:
          'This permanently deletes your account and all associated data. This cannot be undone.',
      destructive: true,
    );
    if (ok != true) return;
    try {
      await authApi.deleteAccount();
      if (!mounted) return;
      await context.read<AuthProvider>().logout();
    } catch (e) {
      _flash('Failed to delete account: $e', error: true);
    }
  }

  Future<bool?> _confirm(
    String title, {
    String? body,
    bool destructive = false,
  }) {
    return showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppColors.surface1,
        title: Text(title, style: const TextStyle(color: AppColors.cream)),
        content: body == null
            ? null
            : Text(body, style: const TextStyle(color: AppColors.creamDim)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(
              foregroundColor: destructive ? AppColors.danger : AppColors.terra,
            ),
            child: Text(destructive ? 'Delete' : 'Confirm'),
          ),
        ],
      ),
    );
  }

  static String _providerLabel(String p) =>
      {
        'google': 'Google Calendar',
        'apple': 'Apple Calendar',
        'outlook': 'Outlook Calendar',
      }[p] ??
      p;

  // ── Build ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().user;
    return Scaffold(
      backgroundColor: AppColors.midnight,
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text(
            'Your Profile',
            style: TextStyle(
              color: AppColors.cream,
              fontSize: 28,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Manage your account.',
            style: TextStyle(color: AppColors.creamDim, fontSize: 14),
          ),
          const SizedBox(height: 20),
          if (_message != null)
            AlertBanner(message: _message!, error: _isError),

          // Profile card
          ACard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Avatar(
                      name: user?['first_name'] ?? user?['email'],
                      size: 56,
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            user?['first_name'] ?? 'Your account',
                            style: const TextStyle(
                              color: AppColors.cream,
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          Text(
                            user?['email'] ?? '',
                            style: const TextStyle(
                              color: AppColors.creamDim,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                LabeledInput(label: 'First name', controller: _firstName),
                LabeledInput(label: 'Last name', controller: _lastName),
                const Text(
                  'TIMEZONE',
                  style: TextStyle(
                    color: AppColors.creamDim,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 6),
                DropdownButtonFormField<String>(
                  initialValue: _timezones.contains(_tz) ? _tz : 'UTC',
                  dropdownColor: AppColors.surface1,
                  style: const TextStyle(color: AppColors.cream),
                  items: [
                    for (final tz in _timezones)
                      DropdownMenuItem(value: tz, child: Text(tz)),
                  ],
                  onChanged: (v) => setState(() => _tz = v ?? 'UTC'),
                ),
                const SizedBox(height: 20),
                APrimaryButton(
                  label: 'Save changes',
                  loading: _saving,
                  onPressed: _saveProfile,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Password card
          ACard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const CardLabel('Change password'),
                const SizedBox(height: 12),
                LabeledInput(
                  label: 'Current password',
                  controller: _currentPw,
                  obscure: true,
                ),
                LabeledInput(
                  label: 'New password',
                  controller: _newPw,
                  obscure: true,
                  hint: 'Min. 8 characters',
                ),
                OutlinedButton(
                  onPressed: _changingPw ? null : _changePassword,
                  child: Text(_changingPw ? 'Changing…' : 'Change password'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Device Calendar (native — one tap)
          if (!kIsWeb)
            ACard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  CardLabel(
                    !kIsWeb &&
                            (defaultTargetPlatform == TargetPlatform.iOS ||
                                defaultTargetPlatform == TargetPlatform.macOS)
                        ? 'Apple & Device Calendars'
                        : 'Device Calendar',
                  ),
                  const SizedBox(height: 6),
                  Text(
                    !kIsWeb &&
                            (defaultTargetPlatform == TargetPlatform.iOS ||
                                defaultTargetPlatform == TargetPlatform.macOS)
                        ? 'Sync iCloud Calendar and all other calendars on this device with one tap — no passwords needed.'
                        : 'Sync events from all calendars on this device (Google, Exchange, etc.) with one tap.',
                    style: const TextStyle(
                      color: AppColors.creamDim,
                      fontSize: 12,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: _deviceSyncing
                              ? null
                              : _syncDeviceCalendar,
                          icon: _deviceSyncing
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: AppColors.cream,
                                  ),
                                )
                              : const Icon(Icons.sync, size: 18),
                          label: Text(_deviceSyncing ? 'Syncing…' : 'Sync now'),
                        ),
                      ),
                    ],
                  ),
                  if (_deviceEventCount != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      '✓ $_deviceEventCount events synced',
                      style: const TextStyle(
                        color: AppColors.sage,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          const SizedBox(height: 16),

          // Cloud calendar providers (Apple CalDAV only shown on web)
          ACard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const CardLabel('Cloud Calendars'),
                const SizedBox(height: 6),
                const Text(
                  'Connect directly to cloud calendar services for automatic background sync.',
                  style: TextStyle(
                    color: AppColors.creamDim,
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 12),
                _CalendarRow(
                  label: 'Google Calendar',
                  status: _calStatus?['google'],
                  busy: _busyProvider == 'google',
                  onConnect: () => _connectOAuth('google'),
                  onSync: () => _sync('google'),
                  onDisconnect: () => _disconnect('google'),
                ),
                if (kIsWeb) ...[
                  const Divider(color: AppColors.border, height: 20),
                  _CalendarRow(
                    label: 'Apple Calendar (CalDAV)',
                    status: _calStatus?['apple'],
                    busy: _busyProvider == 'apple',
                    onConnect: _connectApple,
                    onSync: () => _sync('apple'),
                    onDisconnect: () => _disconnect('apple'),
                    identifierKey: 'username',
                  ),
                ],
                const Divider(color: AppColors.border, height: 20),
                _CalendarRow(
                  label: 'Outlook Calendar',
                  status: _calStatus?['outlook'],
                  busy: _busyProvider == 'outlook',
                  onConnect: () => _connectOAuth('outlook'),
                  onSync: () => _sync('outlook'),
                  onDisconnect: () => _disconnect('outlook'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Account info
          ACard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [CardLabel('Account info'), SizedBox(height: 10)],
            ),
          ),
          const SizedBox(height: 10),
          const _PushNotificationToggle(),
          const SizedBox(height: 16),

          // Sign out
          ACard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const CardLabel('Sign out'),
                const SizedBox(height: 10),
                OutlinedButton(
                  onPressed: () => context.read<AuthProvider>().logout(),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.danger,
                  ),
                  child: const Text('Sign out'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Danger zone
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.surface1,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: AppColors.danger.withValues(alpha: 0.3),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'DANGER ZONE',
                  style: TextStyle(
                    color: AppColors.danger,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 10),
                const Text(
                  'Permanently delete your account and all associated data. This cannot be undone.',
                  style: TextStyle(
                    color: AppColors.creamDim,
                    fontSize: 13,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 14),
                OutlinedButton(
                  onPressed: _deleteAccount,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.danger,
                    side: BorderSide(
                      color: AppColors.danger.withValues(alpha: 0.4),
                    ),
                  ),
                  child: const Text('Delete account'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Calendar row ────────────────────────────────────────────────────────────

class _CalendarRow extends StatelessWidget {
  final String label;
  final dynamic status;
  final bool busy;
  final VoidCallback onConnect;
  final VoidCallback onSync;
  final VoidCallback onDisconnect;
  final String identifierKey;
  const _CalendarRow({
    required this.label,
    required this.status,
    required this.busy,
    required this.onConnect,
    required this.onSync,
    required this.onDisconnect,
    this.identifierKey = 'email',
  });

  @override
  Widget build(BuildContext context) {
    final connected = status is Map && status['connected'] == true;
    final identifier = status is Map ? status[identifierKey]?.toString() : null;
    final syncedAt = status is Map ? status['synced_at']?.toString() : null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        label,
                        style: const TextStyle(
                          color: AppColors.cream,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(width: 8),
                      if (connected)
                        const Text(
                          '✓',
                          style: TextStyle(color: AppColors.sage, fontSize: 14),
                        ),
                    ],
                  ),
                  if (connected &&
                      identifier != null &&
                      identifier.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(
                      identifier,
                      style: const TextStyle(
                        color: AppColors.creamDim,
                        fontSize: 12,
                      ),
                    ),
                  ],
                  if (connected && syncedAt != null && syncedAt.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(
                      'Last synced ${_relativeTime(syncedAt)}',
                      style: const TextStyle(
                        color: AppColors.creamDim,
                        fontSize: 11,
                      ),
                    ),
                  ],
                  if (!connected) ...[
                    const SizedBox(height: 2),
                    const Text(
                      'Not connected',
                      style: TextStyle(color: AppColors.creamDim, fontSize: 12),
                    ),
                  ],
                ],
              ),
            ),
            if (busy)
              const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            else if (connected) ...[
              TextButton(onPressed: onSync, child: const Text('Sync')),
              TextButton(
                onPressed: onDisconnect,
                style: TextButton.styleFrom(foregroundColor: AppColors.danger),
                child: const Text('Disconnect'),
              ),
            ] else
              TextButton(onPressed: onConnect, child: const Text('Connect')),
          ],
        ),
      ],
    );
  }

  static String _relativeTime(String iso) {
    final t = DateTime.tryParse(iso);
    if (t == null) return iso;
    final diff = DateTime.now().difference(t);
    if (diff.inMinutes < 1) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return DateFormat('d MMM').format(t);
  }
}

// ── Push notification toggle ────────────────────────────────────────────────

class _PushNotificationToggle extends StatefulWidget {
  const _PushNotificationToggle();
  @override
  State<_PushNotificationToggle> createState() =>
      _PushNotificationToggleState();
}

class _PushNotificationToggleState extends State<_PushNotificationToggle> {
  bool _enabled = false;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _enabled = PushNotificationService.instance.token != null;
  }

  Future<void> _toggle(bool value) async {
    setState(() => _loading = true);
    try {
      if (value) {
        final ok = await PushNotificationService.instance
            .requestPermissionAndRegister();
        if (!ok && mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'Notification permission denied. Enable in system settings.',
              ),
            ),
          );
        }
        if (mounted) setState(() => _enabled = ok);
      } else {
        await PushNotificationService.instance.disable();
        if (mounted) setState(() => _enabled = false);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ACard(
      child: Row(
        children: [
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Push notifications',
                  style: TextStyle(
                    color: AppColors.cream,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  'Morning outfit alerts and trip reminders',
                  style: TextStyle(color: AppColors.creamDim, fontSize: 12),
                ),
              ],
            ),
          ),
          if (_loading)
            const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppColors.terra,
              ),
            )
          else
            Switch.adaptive(
              value: _enabled,
              onChanged: _toggle,
              activeTrackColor: AppColors.terra,
            ),
        ],
      ),
    );
  }
}

// ── Apple credentials sheet ─────────────────────────────────────────────────

class _AppleCredentialSheet extends StatefulWidget {
  const _AppleCredentialSheet();
  @override
  State<_AppleCredentialSheet> createState() => _AppleCredentialSheetState();
}

class _AppleCredentialSheetState extends State<_AppleCredentialSheet> {
  final _user = TextEditingController();
  final _pw = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _user.dispose();
    _pw.dispose();
    super.dispose();
  }

  void _submit() {
    final username = _user.text.trim().toLowerCase();
    final raw = _pw.text.replaceAll(RegExp(r'[\s\-]+'), '').toLowerCase();
    final password = raw.length == 16
        ? '${raw.substring(0, 4)}-${raw.substring(4, 8)}-${raw.substring(8, 12)}-${raw.substring(12, 16)}'
        : _pw.text.trim();
    if (username.isEmpty || password.isEmpty) {
      setState(
        () => _error = 'Apple ID and App-Specific Password are required.',
      );
      return;
    }
    Navigator.pop(context, {'username': username, 'password': password});
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Connect Apple Calendar',
                style: TextStyle(
                  color: AppColors.cream,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Generate an App-Specific Password at appleid.apple.com under Sign-In & Security.',
                style: TextStyle(
                  color: AppColors.creamDim,
                  fontSize: 12,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 16),
              if (_error != null) AlertBanner(message: _error!),
              LabeledInput(
                label: 'Apple ID',
                controller: _user,
                hint: 'you@icloud.com',
              ),
              LabeledInput(
                label: 'App-Specific Password',
                controller: _pw,
                hint: 'xxxx-xxxx-xxxx-xxxx',
                obscure: true,
              ),
              const SizedBox(height: 8),
              APrimaryButton(label: 'Connect', onPressed: _submit),
            ],
          ),
        ),
      ),
    );
  }
}
