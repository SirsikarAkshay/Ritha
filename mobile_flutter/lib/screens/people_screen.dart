import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../api/api.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class PeopleScreen extends StatefulWidget {
  const PeopleScreen({super.key});
  @override
  State<PeopleScreen> createState() => _PeopleScreenState();
}

class _PeopleScreenState extends State<PeopleScreen> with SingleTickerProviderStateMixin {
  late final TabController _tab;

  @override
  void initState() { super.initState(); _tab = TabController(length: 3, vsync: this); }

  @override
  void dispose() { _tab.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.midnight,
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text('People', style: TextStyle(color: AppColors.cream, fontSize: 28, fontWeight: FontWeight.w700)),
                SizedBox(height: 4),
                Text('Find friends by handle. Connect, chat, plan trips together.',
                    style: TextStyle(color: AppColors.creamDim, fontSize: 14)),
              ],
            ),
          ),
          const _ProfilePanel(),
          TabBar(
            controller: _tab,
            labelColor: AppColors.cream,
            unselectedLabelColor: AppColors.creamDim,
            indicatorColor: AppColors.terra,
            tabs: const [
              Tab(text: 'Find'),
              Tab(text: 'Connected'),
              Tab(text: 'Requests'),
            ],
          ),
          Expanded(
            child: TabBarView(
              controller: _tab,
              children: const [
                _FindTab(),
                _ConnectionsTab(status: 'accepted', withActions: false, emptyLabel: 'No connections yet.'),
                _ConnectionsTab(status: 'pending',  withActions: true,  emptyLabel: 'No pending requests.'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfilePanel extends StatefulWidget {
  const _ProfilePanel();
  @override
  State<_ProfilePanel> createState() => _ProfilePanelState();
}

class _ProfilePanelState extends State<_ProfilePanel> {
  Map<String, dynamic>? _profile;
  bool _editing = false;
  final _handle = TextEditingController();
  final _displayName = TextEditingController();
  final _bio = TextEditingController();
  bool _saving = false;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final p = await socialApi.profile.get() as Map;
      setState(() {
        _profile = Map<String, dynamic>.from(p);
        _handle.text      = _profile!['handle'] ?? '';
        _displayName.text = _profile!['display_name'] ?? '';
        _bio.text         = _profile!['bio'] ?? '';
      });
    } catch (_) {}
  }

  Future<void> _save() async {
    setState(() { _saving = true; _error = null; });
    try {
      final updated = await socialApi.profile.update({
        'display_name': _displayName.text.trim(),
        'bio': _bio.text.trim(),
      }) as Map;
      if (_handle.text.trim() != _profile!['handle']) {
        final afterHandle = await socialApi.profile.updateHandle(_handle.text.trim().toLowerCase()) as Map;
        setState(() => _profile = Map<String, dynamic>.from(afterHandle));
      } else {
        setState(() => _profile = Map<String, dynamic>.from(updated));
      }
      setState(() { _editing = false; });
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_profile == null) {
      return const Padding(padding: EdgeInsets.all(20), child: Text('Loading…', style: TextStyle(color: AppColors.creamDim)));
    }
    if (!_editing) {
      return Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
        child: ACard(
          child: Row(
            children: [
              Avatar(name: _profile!['handle'], size: 48),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_profile!['display_name'] ?? _profile!['handle'] ?? '',
                        style: const TextStyle(color: AppColors.cream, fontSize: 16, fontWeight: FontWeight.w600)),
                    Text('@${_profile!['handle']}',
                        style: const TextStyle(color: AppColors.terraLight, fontSize: 13)),
                    if ((_profile!['bio'] ?? '').toString().isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text(_profile!['bio'], style: const TextStyle(color: AppColors.creamDim, fontSize: 13)),
                    ],
                  ],
                ),
              ),
              TextButton(onPressed: () => setState(() => _editing = true), child: const Text('Edit')),
            ],
          ),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
      child: ACard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_error != null) AlertBanner(message: _error!),
            LabeledInput(label: 'Handle', controller: _handle, hint: 'jane'),
            LabeledInput(label: 'Display name', controller: _displayName),
            LabeledInput(label: 'Bio', controller: _bio, maxLines: 3),
            Row(children: [
              Expanded(child: OutlinedButton(onPressed: () => setState(() { _editing = false; _error = null; }), child: const Text('Cancel'))),
              const SizedBox(width: 10),
              Expanded(child: ElevatedButton(onPressed: _saving ? null : _save, child: Text(_saving ? 'Saving…' : 'Save'))),
            ]),
          ],
        ),
      ),
    );
  }
}

class _FindTab extends StatefulWidget {
  const _FindTab();
  @override
  State<_FindTab> createState() => _FindTabState();
}

class _FindTabState extends State<_FindTab> {
  final _handle = TextEditingController();
  Map<String, dynamic>? _result;
  bool _loading = false;
  bool _requesting = false;
  String? _error;

  Future<void> _search() async {
    setState(() { _loading = true; _error = null; _result = null; });
    try {
      final res = await socialApi.users.search(_handle.text.trim().toLowerCase().replaceAll('@', '')) as Map;
      setState(() => _result = Map<String, dynamic>.from(res));
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _sendRequest() async {
    if (_result?['user']?['handle'] == null) return;
    setState(() => _requesting = true);
    try {
      await socialApi.connections.request(_result!['user']['handle'] as String);
      await _search();
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _requesting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        LabeledInput(label: 'Handle', controller: _handle, hint: 'jane'),
        APrimaryButton(label: 'Search', loading: _loading, onPressed: _search),
        const SizedBox(height: 14),
        if (_error != null) AlertBanner(message: _error!),
        if (_result != null && _result!['found'] != true)
          const ACard(child: Text('No user found with that handle.', style: TextStyle(color: AppColors.creamDim))),
        if (_result != null && _result!['found'] == true)
          ACard(
            child: Row(children: [
              Avatar(name: _result!['user']['handle'], size: 44),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_result!['user']['display_name'] ?? _result!['user']['handle'],
                        style: const TextStyle(color: AppColors.cream, fontSize: 15, fontWeight: FontWeight.w600)),
                    Text('@${_result!['user']['handle']}',
                        style: const TextStyle(color: AppColors.terraLight, fontSize: 13)),
                  ],
                ),
              ),
              if (_result!['is_self'] == true)
                const Text('You', style: TextStyle(color: AppColors.creamDim))
              else
                _ConnectionCta(connection: _result!['user']['connection'], onConnect: _sendRequest, busy: _requesting),
            ]),
          ),
      ],
    );
  }
}

class _ConnectionCta extends StatelessWidget {
  final dynamic connection;
  final VoidCallback onConnect;
  final bool busy;
  const _ConnectionCta({required this.connection, required this.onConnect, required this.busy});
  @override
  Widget build(BuildContext context) {
    if (connection == null) {
      return ElevatedButton(onPressed: busy ? null : onConnect, child: Text(busy ? 'Sending…' : 'Connect'));
    }
    final status = connection['status'];
    final direction = connection['direction'];
    if (status == 'accepted') return const Text('Connected ✓', style: TextStyle(color: AppColors.sage));
    if (status == 'pending' && direction == 'outgoing') return const Text('Request sent', style: TextStyle(color: AppColors.creamDim));
    if (status == 'pending' && direction == 'incoming') return const Text('In Requests tab', style: TextStyle(color: AppColors.terraLight));
    return ElevatedButton(onPressed: busy ? null : onConnect, child: const Text('Connect'));
  }
}

class _ConnectionsTab extends StatefulWidget {
  final String status;
  final bool withActions;
  final String emptyLabel;
  const _ConnectionsTab({required this.status, required this.withActions, required this.emptyLabel});
  @override
  State<_ConnectionsTab> createState() => _ConnectionsTabState();
}

class _ConnectionsTabState extends State<_ConnectionsTab> {
  List<dynamic> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final res = await socialApi.connections.list(widget.status) as Map;
      setState(() { _items = res['results'] ?? []; _loading = false; });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  Future<void> _act(Future Function() fn) async {
    try { await fn(); await _load(); }
    catch (e) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString()))); }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator(color: AppColors.terra));
    if (_error != null) return Padding(padding: const EdgeInsets.all(20), child: AlertBanner(message: _error!));
    if (_items.isEmpty) return Padding(padding: const EdgeInsets.all(20), child: Text(widget.emptyLabel, style: const TextStyle(color: AppColors.creamDim)));
    return RefreshIndicator(
      color: AppColors.terra,
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.all(20),
        itemCount: _items.length,
        itemBuilder: (_, i) {
          final conn = _items[i];
          final other = conn['other_user'];
          return Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: ACard(
              padding: const EdgeInsets.all(14),
              child: Row(children: [
                Avatar(name: other['handle'], size: 40),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(other['display_name'] ?? other['handle'],
                          style: const TextStyle(color: AppColors.cream, fontSize: 14, fontWeight: FontWeight.w600)),
                      Text('@${other['handle']}',
                          style: const TextStyle(color: AppColors.terraLight, fontSize: 12)),
                    ],
                  ),
                ),
                if (widget.withActions && conn['direction'] == 'incoming') ...[
                  TextButton(onPressed: () => _act(() => socialApi.connections.accept(conn['id'] as int)), child: const Text('Accept')),
                  TextButton(onPressed: () => _act(() => socialApi.connections.reject(conn['id'] as int)),
                      style: TextButton.styleFrom(foregroundColor: AppColors.danger), child: const Text('Reject')),
                ],
                if (widget.withActions && conn['direction'] == 'outgoing')
                  TextButton(onPressed: () => _act(() => socialApi.connections.remove(conn['id'] as int)),
                      style: TextButton.styleFrom(foregroundColor: AppColors.danger), child: const Text('Cancel')),
                if (!widget.withActions && widget.status == 'accepted')
                  IconButton(
                    onPressed: () => context.go('/messages?open_user_id=${other['id']}'),
                    icon: const Icon(Icons.chat_bubble_outline, color: AppColors.terraLight),
                  ),
              ]),
            ),
          );
        },
      ),
    );
  }
}
