import 'package:flutter/material.dart';
import '../api/api.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

// Preset bag sizes (mirrors PackingListInputSerializer.BAG_TYPE_LITERS).
const _bagPresets = [
  ('Personal item', 20),
  ('Backpack', 30),
  ('Carry-on', 40),
  ('Checked', 70),
];

const _catIcons = {
  'top': '👕',
  'bottom': '👖',
  'dress': '👗',
  'outerwear': '🧥',
  'footwear': '👟',
  'accessory': '💍',
  'activewear': '🏃',
  'formal': '🤵',
  'other': '📦',
};

/// Bag-capacity-aware packing: fit the most versatile capsule from the user's
/// wardrobe into a chosen bag volume, and show what got left behind.
class PackingCapacityScreen extends StatefulWidget {
  const PackingCapacityScreen({super.key});
  @override
  State<PackingCapacityScreen> createState() => _PackingCapacityScreenState();
}

class _PackingCapacityScreenState extends State<PackingCapacityScreen> {
  final _days = TextEditingController(text: '7');
  final _liters = TextEditingController(text: '30');
  final _location = TextEditingController();
  final _activities = TextEditingController();
  bool _loading = false;
  bool _saving = false;
  String? _error;
  Map<String, dynamic>? _result;

  @override
  void dispose() {
    _days.dispose();
    _liters.dispose();
    _location.dispose();
    _activities.dispose();
    super.dispose();
  }

  Future<void> _pack() async {
    final days = int.tryParse(_days.text.trim()) ?? 1;
    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });
    try {
      final payload = <String, dynamic>{'days': days};
      final liters = int.tryParse(_liters.text.trim());
      if (liters != null && liters > 0) payload['bag_capacity_liters'] = liters;
      final loc = _location.text.trim();
      if (loc.isNotEmpty) payload['location'] = loc;
      final acts = _activities.text
          .split(',')
          .map((s) => s.trim())
          .where((s) => s.isNotEmpty)
          .toList();
      if (acts.isNotEmpty) payload['activities'] = acts;

      final result = await agentsApi.packingList(payload) as Map;
      if (!mounted) return;
      if (result['status'] == 'completed') {
        final out = Map<String, dynamic>.from(result['output'] ?? {});
        if (out['status'] == 'no_wardrobe') {
          setState(() {
            _error = (out['message'] ?? 'Add items to your wardrobe first.')
                .toString();
            _loading = false;
          });
          return;
        }
        setState(() {
          _result = out;
          _loading = false;
        });
      } else {
        setState(() {
          _error = (result['error'] ?? 'Packing failed').toString();
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  // Wardrobe ClothingItem ids from the current packing result.
  List<int> _packedItemIds() {
    final ids = <int>[];
    final raw = _result?['item_ids'];
    if (raw is List) {
      for (final x in raw) {
        final n = (x is num) ? x.toInt() : int.tryParse('$x');
        if (n != null) ids.add(n);
      }
    }
    if (ids.isEmpty) {
      final list = _result?['packing_list'];
      if (list is List) {
        for (final it in list) {
          if (it is Map && it['id'] != null) {
            final n = (it['id'] is num)
                ? (it['id'] as num).toInt()
                : int.tryParse('${it['id']}');
            if (n != null) ids.add(n);
          }
        }
      }
    }
    return ids;
  }

  void _snack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(msg)));
  }

  Future<void> _saveToTrip() async {
    final itemIds = _packedItemIds();
    if (itemIds.isEmpty) {
      _snack('Nothing to save — this list has no wardrobe items.');
      return;
    }
    List trips;
    try {
      final res = await itineraryApi.trips.list();
      trips = res is Map
          ? (res['results'] as List? ?? const [])
          : (res as List? ?? const []);
    } catch (_) {
      _snack('Could not load your trips.');
      return;
    }
    if (!mounted) return;
    if (trips.isEmpty) {
      _snack('Create a trip first (Trips tab), then save your packing list to it.');
      return;
    }
    final trip = await showModalBottomSheet<Map>(
      context: context,
      backgroundColor: AppColors.surface2,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'Save packing list to…',
                style: TextStyle(
                  color: AppColors.cream,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            for (final t in trips)
              if (t is Map)
                ListTile(
                  title: Text(
                    '${t['name'] ?? t['destination'] ?? 'Trip'}',
                    style: const TextStyle(color: AppColors.cream),
                  ),
                  subtitle: Text(
                    '${t['start_date'] ?? ''} → ${t['end_date'] ?? ''}',
                    style: const TextStyle(
                      color: AppColors.creamDim,
                      fontSize: 12,
                    ),
                  ),
                  onTap: () => Navigator.pop(ctx, Map<String, dynamic>.from(t)),
                ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
    if (trip == null || !mounted) return;
    final tripId = (trip['id'] is num)
        ? (trip['id'] as num).toInt()
        : int.tryParse('${trip['id']}');
    if (tripId == null) return;
    setState(() => _saving = true);
    try {
      await itineraryApi.trips.fromPackingList(tripId, itemIds);
      _snack('Packing list saved to ${trip['name'] ?? 'your trip'} 🎒');
    } catch (e) {
      _snack('Could not save: $e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = _result;
    final selectedLiters = int.tryParse(_liters.text.trim());
    return Scaffold(
      backgroundColor: AppColors.midnight,
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text(
            'Pack by Bag Size',
            style: TextStyle(
              color: AppColors.cream,
              fontSize: 28,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Fit the most versatile capsule from your wardrobe into your bag.',
            style: TextStyle(color: AppColors.creamDim, fontSize: 14),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: LabeledInput(
                  label: 'Trip length (days)',
                  controller: _days,
                  keyboardType: TextInputType.number,
                  hint: 'e.g. 14',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: LabeledInput(
                  label: 'Bag capacity (L)',
                  controller: _liters,
                  keyboardType: TextInputType.number,
                  hint: 'e.g. 30',
                ),
              ),
            ],
          ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final p in _bagPresets)
                _PresetChip(
                  label: '${p.$1} · ${p.$2}L',
                  selected: selectedLiters == p.$2,
                  onTap: () => setState(() => _liters.text = '${p.$2}'),
                ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: LabeledInput(
                  label: 'Destination (optional)',
                  controller: _location,
                  hint: 'e.g. Europe',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: LabeledInput(
                  label: 'Activities',
                  controller: _activities,
                  hint: 'hiking, dinner',
                ),
              ),
            ],
          ),
          APrimaryButton(
            label: '🎒 Pack my bag',
            loading: _loading,
            onPressed: _pack,
          ),
          const SizedBox(height: 20),
          if (_error != null) AlertBanner(message: _error!),
          if (r != null) ...[
            _PackingResult(result: r),
            const SizedBox(height: 16),
            APrimaryButton(
              label: '💾 Save to a trip',
              loading: _saving,
              onPressed: _saveToTrip,
            ),
          ] else if (!_loading)
            const EmptyState(
              icon: '🎒',
              title: 'Pack smart',
              body:
                  'Enter your trip length and bag size, then tap Pack my bag to '
                  'see a capsule that fits.',
            ),
        ],
      ),
    );
  }
}

class _PresetChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const _PresetChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: selected ? AppColors.terra : AppColors.surface2,
          borderRadius: BorderRadius.circular(100),
          border: Border.all(
            color: selected ? AppColors.terra : AppColors.border,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? AppColors.cream : AppColors.creamDim,
            fontSize: 12,
          ),
        ),
      ),
    );
  }
}

class _PackingResult extends StatelessWidget {
  final Map<String, dynamic> result;
  const _PackingResult({required this.result});

  @override
  Widget build(BuildContext context) {
    final headline = result['headline']?.toString() ?? 'Your packing list';
    final items = (result['packing_list'] as List?) ?? const [];
    final leftBehind = (result['left_behind'] as List?) ?? const [];
    final util = (result['capacity_utilization_pct'] as num?)?.toDouble();
    final capacity = result['bag_capacity_liters'];
    final volume = result['estimated_volume_liters'];
    final notes = result['notes']?.toString();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          headline,
          style: const TextStyle(
            color: AppColors.cream,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 14),
        if (util != null && capacity != null)
          _CapacityGauge(
            util: util,
            volume: volume,
            capacity: capacity,
            itemCount: items.length,
          ),
        const SizedBox(height: 14),
        for (final it in items)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _PackedItemCard(item: Map<String, dynamic>.from(it as Map)),
          ),
        if (leftBehind.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            'Left behind — won\'t fit (${leftBehind.length})',
            style: const TextStyle(color: AppColors.gold, fontSize: 13),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final it in leftBehind)
                if (it is Map)
                  _LeftBehindChip(item: Map<String, dynamic>.from(it)),
            ],
          ),
        ],
        if (notes != null && notes.isNotEmpty) ...[
          const SizedBox(height: 14),
          Text(
            notes,
            style: const TextStyle(
              color: AppColors.creamDim,
              fontSize: 12,
              height: 1.4,
            ),
          ),
        ],
      ],
    );
  }
}

class _CapacityGauge extends StatelessWidget {
  final double util;
  final Object? volume;
  final Object? capacity;
  final int itemCount;
  const _CapacityGauge({
    required this.util,
    required this.volume,
    required this.capacity,
    required this.itemCount,
  });

  Color get _color {
    if (util > 100) return AppColors.danger;
    if (util >= 90) return AppColors.gold;
    return AppColors.terra;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '$volume L packed · $itemCount items',
              style: const TextStyle(color: AppColors.creamDim, fontSize: 12),
            ),
            Text(
              '${util.round()}% of $capacity L',
              style: TextStyle(
                color: _color,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(100),
          child: LinearProgressIndicator(
            value: (util / 100).clamp(0.0, 1.0),
            minHeight: 10,
            backgroundColor: AppColors.surface3,
            valueColor: AlwaysStoppedAnimation<Color>(_color),
          ),
        ),
      ],
    );
  }
}

class _PackedItemCard extends StatelessWidget {
  final Map<String, dynamic> item;
  const _PackedItemCard({required this.item});

  @override
  Widget build(BuildContext context) {
    final category = item['category']?.toString() ?? 'other';
    final name = item['name']?.toString() ?? '';
    final vol = item['packed_volume_liters'];
    return ACard(
      padding: const EdgeInsets.all(12),
      child: Row(
        children: [
          Text(
            _catIcons[category] ?? '📦',
            style: const TextStyle(fontSize: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              name,
              style: const TextStyle(color: AppColors.cream, fontSize: 14),
            ),
          ),
          Text(
            '$category · ${vol}L',
            style: const TextStyle(color: AppColors.creamDim, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _LeftBehindChip extends StatelessWidget {
  final Map<String, dynamic> item;
  const _LeftBehindChip({required this.item});

  @override
  Widget build(BuildContext context) {
    final name = item['name']?.toString() ?? '';
    final vol = item['packed_volume_liters'];
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(100),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(
        '$name · ${vol}L',
        style: const TextStyle(color: AppColors.creamDim, fontSize: 12),
      ),
    );
  }
}
