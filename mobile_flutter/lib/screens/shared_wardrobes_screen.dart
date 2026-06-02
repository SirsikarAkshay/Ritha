import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../api/api.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

class SharedWardrobesScreen extends StatefulWidget {
  const SharedWardrobesScreen({super.key});
  @override
  State<SharedWardrobesScreen> createState() => _SharedWardrobesScreenState();
}

class _SharedWardrobesScreenState extends State<SharedWardrobesScreen> {
  List<dynamic> _wardrobes = [];
  List<dynamic> _invitations = [];
  bool _loading = true;
  String? _error;
  int? _responding;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final results = await Future.wait([
        sharedWardrobesApi.list(),
        sharedWardrobesApi.invitations.list(),
      ]);
      final list = results[0];
      final invs = results[1];
      setState(() {
        _wardrobes = (list is Map ? list['results'] : list) as List? ?? [];
        _invitations = (invs is List) ? invs : [];
        _loading = false;
      });
    } catch (e) { setState(() { _error = e.toString(); _loading = false; }); }
  }

  Future<void> _respondToInvitation(int id, String action) async {
    setState(() => _responding = id);
    try {
      await sharedWardrobesApi.invitations.respond(id, action);
      setState(() => _invitations.removeWhere((inv) => inv['id'] == id));
      if (action == 'accept') _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(action == 'accept' ? 'Joined the wardrobe.' : 'Invitation declined.')),
        );
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      setState(() => _responding = null);
    }
  }

  Future<void> _create() async {
    final ok = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface1,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => const _CreateSheet(),
    );
    if (ok != null && mounted) {
      context.go('/shared-wardrobes/${ok['id']}');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.midnight,
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.terra,
        onPressed: _create,
        child: const Icon(Icons.add),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.terra))
          : RefreshIndicator(
              color: AppColors.terra,
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  const Text('Shared Wardrobes',
                      style: TextStyle(color: AppColors.cream, fontSize: 28, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  const Text('Collaborate on wardrobes with your connections.',
                      style: TextStyle(color: AppColors.creamDim, fontSize: 14)),
                  const SizedBox(height: 16),
                  if (_error != null) AlertBanner(message: _error!),
                  if (_invitations.isNotEmpty) ...[
                    const Text('Pending Invitations',
                        style: TextStyle(color: AppColors.cream, fontSize: 16, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 10),
                    for (final inv in _invitations)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: ACard(
                          child: Row(children: [
                            Expanded(child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(inv['wardrobe_name'] ?? '',
                                    style: const TextStyle(color: AppColors.cream, fontSize: 15, fontWeight: FontWeight.w600)),
                                const SizedBox(height: 2),
                                Text('Invited by ${inv['invited_by']?['display_name'] ?? '@${inv['invited_by']?['handle']}'}',
                                    style: const TextStyle(color: AppColors.creamDim, fontSize: 12)),
                              ],
                            )),
                            TextButton(
                              onPressed: _responding == inv['id'] ? null : () => _respondToInvitation(inv['id'] as int, 'decline'),
                              child: const Text('Decline', style: TextStyle(color: AppColors.creamDim)),
                            ),
                            ElevatedButton(
                              onPressed: _responding == inv['id'] ? null : () => _respondToInvitation(inv['id'] as int, 'accept'),
                              style: ElevatedButton.styleFrom(backgroundColor: AppColors.terra),
                              child: Text(_responding == inv['id'] ? '…' : 'Accept'),
                            ),
                          ]),
                        ),
                      ),
                    const SizedBox(height: 16),
                  ],
                  if (_wardrobes.isEmpty)
                    const EmptyState(icon: '👗', title: 'No shared wardrobes', body: 'Create one with the + button.'),
                  for (final w in _wardrobes)
                    GestureDetector(
                      onTap: () => context.go('/shared-wardrobes/${w['id']}'),
                      child: Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: ACard(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(children: [
                                Expanded(
                                  child: Text(w['name'] ?? '',
                                      style: const TextStyle(color: AppColors.cream, fontSize: 16, fontWeight: FontWeight.w600)),
                                ),
                                if (w['my_role'] == 'owner') const ABadge(text: 'Owner', variant: BadgeVariant.terra),
                              ]),
                              if ((w['description'] ?? '').toString().isNotEmpty) ...[
                                const SizedBox(height: 6),
                                Text(w['description'],
                                    style: const TextStyle(color: AppColors.creamDim, fontSize: 13)),
                              ],
                              const SizedBox(height: 10),
                              Text(
                                '${w['item_count'] ?? 0} items · ${(w['members'] as List?)?.length ?? 0} members',
                                style: const TextStyle(color: AppColors.creamDim, fontSize: 12),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  const SizedBox(height: 80),
                ],
              ),
            ),
    );
  }
}

class _CreateSheet extends StatefulWidget {
  const _CreateSheet();
  @override
  State<_CreateSheet> createState() => _CreateSheetState();
}

class _CreateSheetState extends State<_CreateSheet> {
  final _name = TextEditingController();
  final _description = TextEditingController();
  bool _saving = false;
  String? _error;

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) { setState(() => _error = 'Name is required.'); return; }
    setState(() { _saving = true; _error = null; });
    try {
      final w = await sharedWardrobesApi.create({
        'name': _name.text.trim(),
        'description': _description.text.trim(),
      }) as Map;
      if (mounted) Navigator.pop(context, Map<String, dynamic>.from(w));
    } catch (e) {
      setState(() { _error = e.toString(); _saving = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Create shared wardrobe',
                style: TextStyle(color: AppColors.cream, fontSize: 20, fontWeight: FontWeight.w700)),
            const SizedBox(height: 16),
            if (_error != null) AlertBanner(message: _error!),
            LabeledInput(label: 'Name', controller: _name, hint: 'Summer in Portugal'),
            LabeledInput(label: 'Description (optional)', controller: _description, maxLines: 3),
            APrimaryButton(label: 'Create', loading: _saving, onPressed: _save),
          ],
        ),
      ),
    );
  }
}
