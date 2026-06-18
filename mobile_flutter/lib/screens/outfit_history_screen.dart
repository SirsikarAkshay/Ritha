import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../api/api.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

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

class OutfitHistoryScreen extends StatefulWidget {
  const OutfitHistoryScreen({super.key});
  @override
  State<OutfitHistoryScreen> createState() => _OutfitHistoryScreenState();
}

class _OutfitHistoryScreenState extends State<OutfitHistoryScreen> {
  List<dynamic> _recs = [];
  Map<String, dynamic>? _prefs;
  bool _loading = true;
  String _filter = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final params = <String, dynamic>{'days': '90'};
      if (_filter.isNotEmpty) params['status'] = _filter;
      final results = await Future.wait([
        outfitsApi.history(params),
        outfitsApi.preferences(),
      ]);
      if (!mounted) return;
      final history = results[0];
      setState(() {
        _recs = history is List
            ? history
            : (history is Map && history['results'] is List
                  ? history['results']
                  : []);
        _prefs = results[1] is Map
            ? Map<String, dynamic>.from(results[1] as Map)
            : null;
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.midnight,
      appBar: AppBar(
        backgroundColor: AppColors.midnight,
        title: const Text(
          'Outfit History',
          style: TextStyle(color: AppColors.cream),
        ),
        iconTheme: const IconThemeData(color: AppColors.cream),
      ),
      body: RefreshIndicator(
        color: AppColors.terra,
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            if (_prefs != null) _StatsCard(prefs: _prefs!),
            const SizedBox(height: 12),
            _FilterChips(
              value: _filter,
              onChanged: (v) {
                setState(() => _filter = v);
                _load();
              },
            ),
            const SizedBox(height: 16),
            if (_loading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(40),
                  child: CircularProgressIndicator(color: AppColors.terra),
                ),
              )
            else if (_recs.isEmpty)
              const ACard(
                child: Padding(
                  padding: EdgeInsets.symmetric(vertical: 30),
                  child: Center(
                    child: Text(
                      'No outfit recommendations yet.',
                      style: TextStyle(color: AppColors.creamDim, fontSize: 14),
                    ),
                  ),
                ),
              )
            else
              ..._recs.map(
                (rec) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _OutfitHistoryTile(
                    rec: Map<String, dynamic>.from(rec as Map),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _StatsCard extends StatelessWidget {
  final Map<String, dynamic> prefs;
  const _StatsCard({required this.prefs});

  @override
  Widget build(BuildContext context) {
    final total = prefs['total_recommendations'] ?? 0;
    final accepted = prefs['accepted'] ?? 0;
    final rejected = prefs['rejected'] ?? 0;
    final rate = prefs['acceptance_rate'];
    final prefCats = (prefs['preferred_categories'] as List?) ?? [];
    final prefColors = (prefs['preferred_colors'] as List?) ?? [];

    return ACard(
      background: AppColors.surface2,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const CardLabel('Your Style Stats'),
          const SizedBox(height: 14),
          Row(
            children: [
              _StatPill(label: 'Total', value: '$total'),
              const SizedBox(width: 10),
              _StatPill(
                label: 'Accepted',
                value: '$accepted',
                color: AppColors.sage,
              ),
              const SizedBox(width: 10),
              _StatPill(
                label: 'Skipped',
                value: '$rejected',
                color: AppColors.terra,
              ),
              if (rate != null) ...[
                const SizedBox(width: 10),
                _StatPill(label: 'Rate', value: '${(rate * 100).round()}%'),
              ],
            ],
          ),
          if (prefCats.isNotEmpty) ...[
            const SizedBox(height: 14),
            const Text(
              'PREFERRED CATEGORIES',
              style: TextStyle(
                color: AppColors.creamDim,
                fontSize: 10,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: prefCats.take(5).map((c) {
                final cat = c['category']?.toString() ?? '';
                final r = c['rate'] is num ? (c['rate'] * 100).round() : 0;
                return ABadge(text: '$cat $r%', variant: BadgeVariant.sage);
              }).toList(),
            ),
          ],
          if (prefColors.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Text(
              'FAVORITE COLORS',
              style: TextStyle(
                color: AppColors.creamDim,
                fontSize: 10,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: prefColors.take(6).map((c) {
                return ABadge(
                  text: c['color']?.toString() ?? '',
                  variant: BadgeVariant.sky,
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _StatPill extends StatelessWidget {
  final String label;
  final String value;
  final Color? color;
  const _StatPill({required this.label, required this.value, this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.surface1,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: TextStyle(
              color: color ?? AppColors.cream,
              fontSize: 18,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: const TextStyle(color: AppColors.creamDim, fontSize: 10),
          ),
        ],
      ),
    );
  }
}

class _FilterChips extends StatelessWidget {
  final String value;
  final ValueChanged<String> onChanged;
  const _FilterChips({required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    const filters = [
      ('', 'All'),
      ('accepted', 'Accepted'),
      ('rejected', 'Skipped'),
      ('pending', 'Pending'),
    ];
    return Row(
      children: filters.map((f) {
        final active = value == f.$1;
        return Padding(
          padding: const EdgeInsets.only(right: 8),
          child: ChoiceChip(
            label: Text(f.$2),
            selected: active,
            selectedColor: AppColors.terra,
            backgroundColor: AppColors.surface2,
            labelStyle: TextStyle(
              color: active ? Colors.white : AppColors.creamDim,
              fontSize: 12,
            ),
            onSelected: (_) => onChanged(f.$1),
            side: BorderSide.none,
          ),
        );
      }).toList(),
    );
  }
}

class _OutfitHistoryTile extends StatelessWidget {
  final Map<String, dynamic> rec;
  const _OutfitHistoryTile({required this.rec});

  @override
  Widget build(BuildContext context) {
    final date = DateTime.tryParse(rec['date']?.toString() ?? '');
    final dateLabel = date != null
        ? DateFormat('EEE, d MMM y').format(date)
        : rec['date']?.toString() ?? '';
    final accepted = rec['accepted'];
    final source = rec['source']?.toString() ?? '';
    final notes = rec['notes']?.toString() ?? '';
    final items = (rec['outfit_items'] as List?) ?? [];
    final weather = rec['weather_snapshot'] is Map
        ? rec['weather_snapshot'] as Map
        : null;

    return ACard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      dateLabel,
                      style: const TextStyle(
                        color: AppColors.cream,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        ABadge(text: source, variant: BadgeVariant.sky),
                        const SizedBox(width: 6),
                        if (weather != null)
                          Text(
                            '${weather['temp_c'] ?? '?'}°C',
                            style: const TextStyle(
                              color: AppColors.creamDim,
                              fontSize: 12,
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              if (accepted == true)
                const ABadge(text: 'Accepted', variant: BadgeVariant.sage),
              if (accepted == false)
                const ABadge(text: 'Skipped', variant: BadgeVariant.terra),
              if (accepted == null)
                const ABadge(text: 'Pending', variant: BadgeVariant.sky),
            ],
          ),
          if (notes.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              '"$notes"',
              style: const TextStyle(
                color: AppColors.creamDim,
                fontSize: 13,
                fontStyle: FontStyle.italic,
                height: 1.4,
              ),
            ),
          ],
          if (items.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: items.map<Widget>((oi) {
                final cat = oi['item_category']?.toString() ?? 'other';
                final name =
                    oi['item_name']?.toString() ??
                    'Item #${oi['clothing_item']}';
                final role = oi['role']?.toString() ?? '';
                final liked = oi['liked'];
                return Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: liked == true
                        ? AppColors.sage.withValues(alpha: 0.15)
                        : liked == false
                        ? AppColors.terra.withValues(alpha: 0.15)
                        : AppColors.surface2,
                    border: Border.all(color: AppColors.border),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        _catIcons[cat] ?? '📦',
                        style: const TextStyle(fontSize: 14),
                      ),
                      const SizedBox(width: 6),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            name,
                            style: const TextStyle(
                              color: AppColors.cream,
                              fontSize: 11,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          Text(
                            role,
                            style: const TextStyle(
                              color: AppColors.creamDim,
                              fontSize: 10,
                            ),
                          ),
                        ],
                      ),
                      if (liked == true)
                        const Padding(
                          padding: EdgeInsets.only(left: 4),
                          child: Icon(
                            Icons.thumb_up,
                            size: 12,
                            color: AppColors.sage,
                          ),
                        ),
                      if (liked == false)
                        const Padding(
                          padding: EdgeInsets.only(left: 4),
                          child: Icon(
                            Icons.thumb_down,
                            size: 12,
                            color: AppColors.terra,
                          ),
                        ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }
}
