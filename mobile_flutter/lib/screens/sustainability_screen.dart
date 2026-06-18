import 'package:flutter/material.dart';
import '../api/api.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

const _actionIcons = {
  'wear_again': '🔄',
  'carry_on_only': '🧳',
  'weight_saved': '⚖',
  'rental': '♻',
  'secondhand': '🛍',
};

const _actionLabels = {
  'wear_again': 'Re-wore an item',
  'carry_on_only': 'Carry-on only',
  'weight_saved': 'Reduced luggage',
  'rental': 'Chose rental',
  'secondhand': 'Bought secondhand',
};

class SustainabilityScreen extends StatefulWidget {
  const SustainabilityScreen({super.key});
  @override
  State<SustainabilityScreen> createState() => _SustainabilityScreenState();
}

class _SustainabilityScreenState extends State<SustainabilityScreen> {
  Map<String, dynamic>? _profile;
  List<dynamic> _logs = [];
  List<dynamic> _items = [];
  final Set<int> _selected = {};
  String _airline = 'default';
  Map<String, dynamic>? _weightResult;
  bool _loading = true;
  bool _calculating = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        sustainabilityApi.tracker().catchError((_) => null),
        sustainabilityApi.logs().catchError((_) => null),
        wardrobeApi.list().catchError((_) => null),
      ]);
      setState(() {
        _profile = results[0] is Map
            ? Map<String, dynamic>.from(results[0] as Map)
            : null;
        final l = results[1];
        _logs = (l is Map ? l['results'] : l) as List? ?? [];
        final w = results[2];
        _items = (w is Map ? w['results'] : w) as List? ?? [];
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _calculate() async {
    if (_selected.isEmpty) return;
    setState(() {
      _calculating = true;
      _error = null;
    });
    try {
      final r =
          await wardrobeApi.luggageWeight(_selected.toList(), _airline) as Map;
      setState(() => _weightResult = Map<String, dynamic>.from(r));
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _calculating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading)
      return const Scaffold(
        backgroundColor: AppColors.midnight,
        body: Center(child: CircularProgressIndicator(color: AppColors.terra)),
      );
    final co2 = ((_profile?['total_co2_saved_kg'] ?? 0) as num).toStringAsFixed(
      2,
    );
    final pts = ((_profile?['total_points'] ?? 0) as num).toInt();
    final level = pts < 50
        ? 'Seedling 🌱'
        : pts < 200
        ? 'Sapling 🌿'
        : pts < 500
        ? 'Tree 🌳'
        : 'Forest 🌲';

    return Scaffold(
      backgroundColor: AppColors.midnight,
      body: RefreshIndicator(
        onRefresh: _load,
        color: AppColors.terra,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Text(
              'Your Impact',
              style: TextStyle(
                color: AppColors.cream,
                fontSize: 28,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Track CO₂ saved, streaks, and luggage weight.',
              style: TextStyle(color: AppColors.creamDim, fontSize: 14),
            ),
            const SizedBox(height: 20),
            if (_error != null) AlertBanner(message: _error!),
            Row(
              children: [
                Expanded(
                  child: _StatPill(value: '$co2 kg', label: 'CO₂ saved'),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _StatPill(value: '$pts', label: 'Eco points'),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _StatPill(
                    value: level.split(' ').first,
                    label: 'Level',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            ACard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const CardLabel('Luggage weight calculator'),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: _airline,
                    dropdownColor: AppColors.surface1,
                    style: const TextStyle(color: AppColors.cream),
                    items: const [
                      DropdownMenuItem(
                        value: 'default',
                        child: Text('Generic (10 kg)'),
                      ),
                      DropdownMenuItem(
                        value: 'easyjet',
                        child: Text('EasyJet'),
                      ),
                      DropdownMenuItem(
                        value: 'ryanair',
                        child: Text('Ryanair'),
                      ),
                      DropdownMenuItem(value: 'swiss', child: Text('Swiss')),
                      DropdownMenuItem(
                        value: 'lufthansa',
                        child: Text('Lufthansa'),
                      ),
                      DropdownMenuItem(
                        value: 'ba',
                        child: Text('British Airways'),
                      ),
                    ],
                    onChanged: (v) => setState(() => _airline = v ?? 'default'),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Select items',
                    style: TextStyle(color: AppColors.creamDim, fontSize: 12),
                  ),
                  const SizedBox(height: 6),
                  Container(
                    constraints: const BoxConstraints(maxHeight: 200),
                    child: _items.isEmpty
                        ? const Text(
                            'Add wardrobe items first.',
                            style: TextStyle(color: AppColors.creamDim),
                          )
                        : ListView(
                            children: [
                              for (final item in _items)
                                CheckboxListTile(
                                  dense: true,
                                  contentPadding: EdgeInsets.zero,
                                  value: _selected.contains(item['id']),
                                  activeColor: AppColors.sage,
                                  title: Text(
                                    item['name'] ?? '',
                                    style: const TextStyle(
                                      color: AppColors.cream,
                                      fontSize: 13,
                                    ),
                                  ),
                                  subtitle: Text(
                                    '${item['weight_grams'] ?? '?'}g',
                                    style: const TextStyle(
                                      color: AppColors.creamDim,
                                      fontSize: 11,
                                    ),
                                  ),
                                  onChanged: (v) => setState(() {
                                    if (v == true)
                                      _selected.add(item['id'] as int);
                                    else
                                      _selected.remove(item['id']);
                                  }),
                                ),
                            ],
                          ),
                  ),
                  const SizedBox(height: 12),
                  APrimaryButton(
                    label: 'Calculate (${_selected.length} items)',
                    loading: _calculating,
                    onPressed: _selected.isEmpty ? null : _calculate,
                  ),
                  if (_weightResult != null) ...[
                    const SizedBox(height: 12),
                    ACard(
                      background: AppColors.surface2,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text(
                                'Total',
                                style: TextStyle(
                                  color: AppColors.creamDim,
                                  fontSize: 13,
                                ),
                              ),
                              Text(
                                '${_weightResult!['total_kg']} kg',
                                style: const TextStyle(
                                  color: AppColors.cream,
                                  fontSize: 20,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _weightResult!['fits_carry_on'] == true
                                ? '✓ Fits carry-on'
                                : '✗ Over carry-on limit',
                            style: TextStyle(
                              color: _weightResult!['fits_carry_on'] == true
                                  ? AppColors.sage
                                  : AppColors.terra,
                              fontSize: 13,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '🌱 CO₂ saved vs. checked bag: ${_weightResult!['co2_saved_vs_checked_kg']} kg',
                            style: const TextStyle(
                              color: AppColors.creamDim,
                              fontSize: 12,
                            ),
                          ),
                          if (_weightResult!['tip'] != null) ...[
                            const SizedBox(height: 4),
                            Text(
                              _weightResult!['tip'].toString(),
                              style: const TextStyle(
                                color: AppColors.creamDim,
                                fontSize: 12,
                                fontStyle: FontStyle.italic,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 20),
            ACard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const CardLabel('Recent activity'),
                  const SizedBox(height: 10),
                  if (_logs.isEmpty)
                    const Center(
                      child: Padding(
                        padding: EdgeInsets.symmetric(vertical: 20),
                        child: Column(
                          children: [
                            Text('🌱', style: TextStyle(fontSize: 32)),
                            SizedBox(height: 8),
                            Text(
                              'Accept outfit recommendations to earn eco points.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: AppColors.creamDim,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                  else
                    for (final log in _logs)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: Row(
                          children: [
                            Text(
                              _actionIcons[log['action']] ?? '✦',
                              style: const TextStyle(fontSize: 18),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _actionLabels[log['action']] ??
                                    log['action'].toString(),
                                style: const TextStyle(
                                  color: AppColors.cream,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                            Text(
                              '+${log['points']}',
                              style: const TextStyle(
                                color: AppColors.sage,
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatPill extends StatelessWidget {
  final String value;
  final String label;
  const _StatPill({required this.value, required this.label});
  @override
  Widget build(BuildContext context) {
    return ACard(
      padding: const EdgeInsets.all(14),
      background: AppColors.surface2,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            style: const TextStyle(
              color: AppColors.cream,
              fontSize: 20,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label.toUpperCase(),
            style: const TextStyle(
              color: AppColors.creamDim,
              fontSize: 10,
              letterSpacing: 0.8,
            ),
          ),
        ],
      ),
    );
  }
}
