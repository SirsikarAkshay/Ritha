import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../api/api.dart';
import '../api/ws.dart';
import '../state/auth_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

const _sharedCategories = ['top', 'bottom', 'outerwear', 'footwear', 'accessory', 'other'];

class SharedWardrobeDetailScreen extends StatefulWidget {
  final int id;
  const SharedWardrobeDetailScreen({super.key, required this.id});
  @override
  State<SharedWardrobeDetailScreen> createState() => _SharedWardrobeDetailScreenState();
}

class _SharedWardrobeDetailScreenState extends State<SharedWardrobeDetailScreen> {
  Map<String, dynamic>? _wardrobe;
  List<dynamic> _items = [];
  bool _loading = true;
  String? _error;
  RithaWebSocket? _ws;
  StreamSubscription? _sub;

  @override
  void initState() {
    super.initState();
    _load();
    _ws = RithaWebSocket('/ws/shared-wardrobe/${widget.id}/');
    _sub = _ws!.onMessage.listen((data) {
      if (data is! Map || data['type'] != 'wardrobe.event') return;
      final eventType = data['event_type'];
      final payload = data['payload'];
      setState(() {
        if (eventType == 'item_added' && payload is Map) {
          if (!_items.any((i) => i['id'] == payload['id'])) _items.add(Map<String, dynamic>.from(payload));
        } else if (eventType == 'item_updated' && payload is Map) {
          final idx = _items.indexWhere((i) => i['id'] == payload['id']);
          if (idx >= 0) _items[idx] = Map<String, dynamic>.from(payload);
        } else if (eventType == 'item_removed' && payload is Map) {
          _items.removeWhere((i) => i['id'] == payload['item_id']);
        } else if (eventType == 'member_added' && payload is Map) {
          final members = (_wardrobe?['members'] as List?) ?? [];
          _wardrobe = {..._wardrobe!, 'members': [...members, payload]};
        } else if (eventType == 'member_removed' && payload is Map) {
          final members = (_wardrobe?['members'] as List?) ?? [];
          _wardrobe = {..._wardrobe!, 'members': members.where((m) => m['user']?['id'] != payload['user_id']).toList()};
        } else if (eventType == 'wardrobe_deleted') {
          if (mounted) context.go('/shared-wardrobes');
        }
      });
    });
  }

  @override
  void dispose() { _sub?.cancel(); _ws?.close(); super.dispose(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final results = await Future.wait([
        sharedWardrobesApi.get(widget.id),
        sharedWardrobesApi.items.list(widget.id),
      ]);
      setState(() {
        _wardrobe = Map<String, dynamic>.from(results[0] as Map);
        _items = results[1] as List? ?? [];
        _loading = false;
      });
    } catch (e) { setState(() { _error = e.toString(); _loading = false; }); }
  }

  Future<void> _deleteItem(int itemId) async {
    try {
      await sharedWardrobesApi.items.delete(widget.id, itemId);
      setState(() => _items.removeWhere((i) => i['id'] == itemId));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _addItem() async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: AppColors.surface1,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => _AddSharedItemSheet(wardrobeId: widget.id),
    );
    if (ok == true) _load();
  }

  Future<void> _editItem(Map<String, dynamic> item) async {
    final updated = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      backgroundColor: AppColors.surface1,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => _EditSharedItemSheet(wardrobeId: widget.id, item: item),
    );
    if (updated != null && mounted) {
      setState(() {
        final idx = _items.indexWhere((i) => i['id'] == updated['id']);
        if (idx >= 0) _items[idx] = updated;
      });
    }
  }

  Future<void> _deleteWardrobe() async {
    final confirm = await _confirm('Delete wardrobe?', 'This cannot be undone.');
    if (confirm != true) return;
    try {
      await sharedWardrobesApi.delete(widget.id);
      if (mounted) context.go('/shared-wardrobes');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _leave() async {
    final userId = context.read<AuthProvider>().user?['id'];
    final confirm = await _confirm('Leave wardrobe?', '');
    if (confirm != true) return;
    if (userId == null) return;
    try {
      await sharedWardrobesApi.members.remove(widget.id, userId as int);
      if (mounted) context.go('/shared-wardrobes');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<bool?> _confirm(String title, String body) => showDialog<bool>(
        context: context,
        builder: (_) => AlertDialog(
          backgroundColor: AppColors.surface1,
          title: Text(title, style: const TextStyle(color: AppColors.cream)),
          content: Text(body, style: const TextStyle(color: AppColors.creamDim)),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
            TextButton(onPressed: () => Navigator.pop(context, true),
                style: TextButton.styleFrom(foregroundColor: AppColors.danger), child: const Text('Confirm')),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(backgroundColor: AppColors.midnight, body: Center(child: CircularProgressIndicator(color: AppColors.terra)));
    }
    if (_error != null) {
      return Scaffold(backgroundColor: AppColors.midnight, body: Padding(padding: const EdgeInsets.all(20), child: AlertBanner(message: _error!)));
    }
    final isOwner = _wardrobe!['my_role'] == 'owner';
    final userId = context.watch<AuthProvider>().user?['id'];
    return Scaffold(
      backgroundColor: AppColors.midnight,
      appBar: AppBar(
        backgroundColor: AppColors.midnight,
        elevation: 0,
        leading: IconButton(onPressed: () => context.go('/shared-wardrobes'), icon: const Icon(Icons.arrow_back, color: AppColors.cream)),
        title: Text(_wardrobe!['name'] ?? '', style: const TextStyle(color: AppColors.cream)),
      ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.terra,
        onPressed: _addItem,
        child: const Icon(Icons.add),
      ),
      body: RefreshIndicator(
        color: AppColors.terra,
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            if ((_wardrobe!['description'] ?? '').toString().isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: Text(_wardrobe!['description'],
                    style: const TextStyle(color: AppColors.creamDim, fontSize: 14)),
              ),
            ACard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const CardLabel('Members'),
                  const SizedBox(height: 10),
                  for (final m in (_wardrobe!['members'] as List? ?? []))
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(children: [
                        Avatar(name: m['user']?['handle'], size: 32),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(m['user']?['display_name'] ?? '@${m['user']?['handle']}',
                              style: const TextStyle(color: AppColors.cream, fontSize: 13)),
                        ),
                        Text(m['role'] ?? '', style: const TextStyle(color: AppColors.creamDim, fontSize: 11)),
                      ]),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Text('Items (${_items.length})',
                style: const TextStyle(color: AppColors.cream, fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 10),
            if (_items.isEmpty)
              const EmptyState(icon: '📦', title: 'No items yet', body: 'Add the first one with the + button.'),
            for (final item in _items)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: ACard(
                  padding: const EdgeInsets.all(14),
                  child: Row(children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(item['name'] ?? '',
                              style: const TextStyle(color: AppColors.cream, fontSize: 15, fontWeight: FontWeight.w600)),
                          Text('${item['category']} · by @${item['added_by']?['handle'] ?? ''}',
                              style: const TextStyle(color: AppColors.creamDim, fontSize: 12)),
                          if ((item['notes'] ?? '').toString().isNotEmpty)
                            Text(item['notes'],
                                style: const TextStyle(color: AppColors.creamDim, fontSize: 12, fontStyle: FontStyle.italic)),
                        ],
                      ),
                    ),
                    if (isOwner || item['added_by']?['id'] == userId) ...[
                      IconButton(
                        onPressed: () => _editItem(Map<String, dynamic>.from(item as Map)),
                        icon: const Icon(Icons.edit_outlined, color: AppColors.creamDim, size: 20),
                      ),
                      IconButton(
                        onPressed: () => _deleteItem(item['id'] as int),
                        icon: const Icon(Icons.delete_outline, color: AppColors.danger, size: 20),
                      ),
                    ],
                  ]),
                ),
              ),
            const SizedBox(height: 20),
            OutlinedButton(
              onPressed: isOwner ? _deleteWardrobe : _leave,
              style: OutlinedButton.styleFrom(foregroundColor: AppColors.danger),
              child: Text(isOwner ? 'Delete wardrobe' : 'Leave wardrobe'),
            ),
            const SizedBox(height: 80),
          ],
        ),
      ),
    );
  }
}

class _AddSharedItemSheet extends StatefulWidget {
  final int wardrobeId;
  const _AddSharedItemSheet({required this.wardrobeId});
  @override
  State<_AddSharedItemSheet> createState() => _AddSharedItemSheetState();
}

class _AddSharedItemSheetState extends State<_AddSharedItemSheet> {
  final _name = TextEditingController();
  final _brand = TextEditingController();
  final _notes = TextEditingController();
  String _category = 'top';
  bool _saving = false;
  String? _error;

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) { setState(() => _error = 'Name required.'); return; }
    setState(() { _saving = true; _error = null; });
    try {
      await sharedWardrobesApi.items.add(widget.wardrobeId, {
        'name': _name.text.trim(),
        'category': _category,
        'brand': _brand.text.trim(),
        'notes': _notes.text.trim(),
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) { setState(() { _error = e.toString(); _saving = false; }); }
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
            const Text('Add item', style: TextStyle(color: AppColors.cream, fontSize: 20, fontWeight: FontWeight.w700)),
            const SizedBox(height: 16),
            if (_error != null) AlertBanner(message: _error!),
            LabeledInput(label: 'Name', controller: _name),
            LabeledInput(label: 'Brand', controller: _brand),
            LabeledInput(label: 'Notes', controller: _notes),
            const Text('CATEGORY',
                style: TextStyle(color: AppColors.creamDim, fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
            const SizedBox(height: 6),
            DropdownButtonFormField<String>(
              initialValue: _category,
              dropdownColor: AppColors.surface1,
              style: const TextStyle(color: AppColors.cream),
              items: [for (final c in _sharedCategories) DropdownMenuItem(value: c, child: Text(c))],
              onChanged: (v) => setState(() => _category = v ?? 'top'),
            ),
            const SizedBox(height: 20),
            APrimaryButton(label: 'Add item', loading: _saving, onPressed: _save),
          ],
        ),
      ),
    );
  }
}

class _EditSharedItemSheet extends StatefulWidget {
  final int wardrobeId;
  final Map<String, dynamic> item;
  const _EditSharedItemSheet({required this.wardrobeId, required this.item});
  @override
  State<_EditSharedItemSheet> createState() => _EditSharedItemSheetState();
}

class _EditSharedItemSheetState extends State<_EditSharedItemSheet> {
  late final TextEditingController _name;
  late final TextEditingController _brand;
  late final TextEditingController _notes;
  late String _category;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.item['name']?.toString() ?? '');
    _brand = TextEditingController(text: widget.item['brand']?.toString() ?? '');
    _notes = TextEditingController(text: widget.item['notes']?.toString() ?? '');
    _category = widget.item['category']?.toString() ?? 'other';
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) { setState(() => _error = 'Name required.'); return; }
    setState(() { _saving = true; _error = null; });
    try {
      final updated = await sharedWardrobesApi.items.update(
        widget.wardrobeId,
        widget.item['id'] as int,
        {
          'name': _name.text.trim(),
          'category': _category,
          'brand': _brand.text.trim(),
          'notes': _notes.text.trim(),
        },
      );
      if (mounted) Navigator.pop(context, updated is Map ? Map<String, dynamic>.from(updated) : null);
    } catch (e) { setState(() { _error = e.toString(); _saving = false; }); }
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
            const Text('Edit item', style: TextStyle(color: AppColors.cream, fontSize: 20, fontWeight: FontWeight.w700)),
            const SizedBox(height: 16),
            if (_error != null) AlertBanner(message: _error!),
            LabeledInput(label: 'Name', controller: _name),
            LabeledInput(label: 'Brand', controller: _brand),
            LabeledInput(label: 'Notes', controller: _notes),
            const Text('CATEGORY',
                style: TextStyle(color: AppColors.creamDim, fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
            const SizedBox(height: 6),
            DropdownButtonFormField<String>(
              initialValue: _category,
              dropdownColor: AppColors.surface1,
              style: const TextStyle(color: AppColors.cream),
              items: [for (final c in _sharedCategories) DropdownMenuItem(value: c, child: Text(c))],
              onChanged: (v) => setState(() => _category = v ?? 'other'),
            ),
            const SizedBox(height: 20),
            APrimaryButton(label: 'Save changes', loading: _saving, onPressed: _save),
          ],
        ),
      ),
    );
  }
}
