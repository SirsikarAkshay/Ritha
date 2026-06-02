import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../api/api.dart';
import '../state/auth_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';

const _catIcons = {
  'top': '👕', 'bottom': '👖', 'dress': '👗', 'outerwear': '🧥',
  'footwear': '👟', 'accessory': '💍', 'activewear': '🏃', 'formal': '🤵', 'other': '📦',
};

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<dynamic> _weekDays = [];
  List<dynamic> _events = [];
  int _selectedIdx = 0;
  bool _loading = true;
  bool _generating = false;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  String get _todayStr => DateFormat('yyyy-MM-dd').format(DateTime.now());

  Future<void> _load() async {
    final today = DateTime.now();
    final end = today.add(const Duration(days: 6));
    try {
      final results = await Future.wait([
        outfitsApi.weekly().catchError((_) => <dynamic>[]),
        itineraryApi.events.list({
          'start_date': DateFormat('yyyy-MM-dd').format(today),
          'end_date': DateFormat('yyyy-MM-dd').format(end),
        }).catchError((_) => null),
      ]);
      if (!mounted) return;
      final days = results[0];
      final evs = results[1];
      setState(() {
        _weekDays = days is List ? days : [];
        if (evs is Map && evs['results'] is List) _events = evs['results'] as List;
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _generateWeek() async {
    setState(() { _generating = true; _error = null; });
    try {
      final result = await agentsApi.weeklyLooks({'location': 'Zurich'}) as Map;
      if (result['status'] == 'completed' || (result['output'] is Map && result['output']['status'] == 'ok')) {
        final fresh = await outfitsApi.weekly();
        setState(() => _weekDays = fresh is List ? fresh : []);
      } else {
        setState(() => _error = (result['error'] ?? result['output']?['message'] ?? 'Failed').toString());
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _generating = false);
    }
  }

  Future<void> _feedback(int recId, bool accepted) async {
    try {
      final updated = await outfitsApi.feedback(recId, accepted) as Map;
      setState(() {
        _weekDays = _weekDays.map((d) {
          if (d is Map && d['recommendation'] is Map && d['recommendation']['id'] == recId) {
            return {...Map<String, dynamic>.from(d), 'recommendation': Map<String, dynamic>.from(updated)};
          }
          return d;
        }).toList();
      });
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().user;
    final dateStr = DateFormat('EEEE, d MMMM y').format(DateTime.now());
    final hasAnyRec = _weekDays.any((d) => d is Map && d['recommendation'] != null);

    return RefreshIndicator(
      color: AppColors.terra,
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(dateStr.toUpperCase(), style: const TextStyle(color: AppColors.creamDim, fontSize: 12, letterSpacing: 1)),
          const SizedBox(height: 4),
          Text(
            user?['first_name'] != null ? 'Good morning, ${user!['first_name']}.' : 'Good morning.',
            style: const TextStyle(color: AppColors.cream, fontSize: 28, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          const Text('Your weekly outfit plan — unique looks for every day.',
              style: TextStyle(color: AppColors.creamDim, fontSize: 15)),
          const SizedBox(height: 20),
          if (_error != null) AlertBanner(message: _error!),

          // Day selector
          if (_weekDays.isNotEmpty)
            SizedBox(
              height: 80,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _weekDays.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, idx) {
                  final day = _weekDays[idx] as Map;
                  final dateVal = day['date']?.toString() ?? '';
                  final isToday = dateVal == _todayStr;
                  final hasRec = day['recommendation'] != null;
                  final accepted = hasRec ? (day['recommendation'] as Map)['accepted'] : null;
                  final selected = idx == _selectedIdx;
                  return GestureDetector(
                    onTap: () => setState(() => _selectedIdx = idx),
                    child: Container(
                      width: 68,
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: selected ? AppColors.terra : AppColors.border, width: selected ? 2 : 1),
                        color: selected ? AppColors.surface2 : AppColors.surface1,
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            isToday ? 'Today' : (day['day_label']?.toString().substring(0, 3) ?? ''),
                            style: TextStyle(
                              color: isToday ? AppColors.terraLight : AppColors.creamDim,
                              fontSize: 10, fontWeight: FontWeight.w600,
                              letterSpacing: 0.5,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            _shortDate(dateVal),
                            style: const TextStyle(color: AppColors.cream, fontSize: 14, fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 4),
                          if (!hasRec) const Text('—', style: TextStyle(color: AppColors.creamDim, fontSize: 10))
                          else if (accepted == true) const Text('✓', style: TextStyle(color: AppColors.sage, fontSize: 12))
                          else if (accepted == false) const Text('✗', style: TextStyle(color: AppColors.danger, fontSize: 12))
                          else const Text('●', style: TextStyle(color: AppColors.terraLight, fontSize: 10)),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),

          const SizedBox(height: 16),

          // Generate button
          if (!_loading)
            Align(
              alignment: Alignment.centerRight,
              child: APrimaryButton(
                label: hasAnyRec ? 'Regenerate week' : 'Generate weekly looks',
                loading: _generating,
                onPressed: _generateWeek,
              ),
            ),

          const SizedBox(height: 16),

          // Selected day detail
          if (_loading)
            const ACard(
              padding: EdgeInsets.symmetric(vertical: 60),
              child: Center(child: CircularProgressIndicator(color: AppColors.terra)),
            )
          else if (_weekDays.isEmpty || _selectedIdx >= _weekDays.length)
            const ACard(
              child: Column(children: [
                SizedBox(height: 20),
                Text('👗', style: TextStyle(fontSize: 48)),
                SizedBox(height: 16),
                Text('No weekly plan yet', style: TextStyle(color: AppColors.cream, fontSize: 20, fontWeight: FontWeight.w700)),
                SizedBox(height: 8),
                Text('Generate your weekly looks to get unique outfits for every day.',
                    textAlign: TextAlign.center, style: TextStyle(color: AppColors.creamDim, fontSize: 14)),
                SizedBox(height: 20),
              ]),
            )
          else
            _DayDetailCard(
              day: Map<String, dynamic>.from(_weekDays[_selectedIdx] as Map),
              events: _events,
              todayStr: _todayStr,
              onFeedback: _feedback,
            ),

          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: () => context.push('/outfit-history'),
              icon: const Icon(Icons.history, size: 16),
              label: const Text('Outfit history'),
            ),
          ),
        ],
      ),
    );
  }

  String _shortDate(String dateStr) {
    final d = DateTime.tryParse(dateStr);
    return d == null ? dateStr : DateFormat('d MMM').format(d);
  }
}


class _DayDetailCard extends StatelessWidget {
  final Map<String, dynamic> day;
  final List<dynamic> events;
  final String todayStr;
  final Future<void> Function(int recId, bool accepted) onFeedback;

  const _DayDetailCard({
    required this.day, required this.events, required this.todayStr,
    required this.onFeedback,
  });

  @override
  Widget build(BuildContext context) {
    final rec = day['recommendation'] is Map ? Map<String, dynamic>.from(day['recommendation'] as Map) : null;
    final dayLabel = day['day_label']?.toString() ?? '';
    final dateVal = day['date']?.toString() ?? '';
    final items = rec != null ? (rec['outfit_items'] as List? ?? []) : [];
    final accepted = rec?['accepted'];
    final weather = rec?['weather_snapshot'] is Map ? Map<String, dynamic>.from(rec!['weather_snapshot'] as Map) : null;
    final dayEvents = events.where((e) => (e['start_time'] as String?)?.startsWith(dateVal) == true).toList();

    return ACard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CardLabel("$dayLabel's outfit"),
                Text(_shortDate(dateVal), style: const TextStyle(color: AppColors.creamDim, fontSize: 12)),
              ],
            )),
            if (accepted == true) const ABadge(text: 'Accepted', variant: BadgeVariant.sage),
            if (accepted == false) const ABadge(text: 'Skipped', variant: BadgeVariant.terra),
          ]),
          const SizedBox(height: 12),

          // Weather mini
          if (weather != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(children: [
                Text(
                  weather['is_raining'] == true ? '🌧' : weather['is_cold'] == true ? '🧥' : weather['is_hot'] == true ? '☀' : '⛅',
                  style: const TextStyle(fontSize: 22),
                ),
                const SizedBox(width: 8),
                Text('${weather['temp_c']}°C', style: const TextStyle(color: AppColors.cream, fontSize: 16, fontWeight: FontWeight.w600)),
                const SizedBox(width: 8),
                Expanded(child: Text('${weather['condition']} · ${weather['precipitation_probability'] ?? 0}% rain',
                    style: const TextStyle(color: AppColors.creamDim, fontSize: 12))),
              ]),
            ),

          // Events
          if (dayEvents.isEmpty)
            const Padding(
              padding: EdgeInsets.only(bottom: 10),
              child: Text('No events — free day ☀', style: TextStyle(color: AppColors.creamDim, fontSize: 13)),
            )
          else
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Column(
                children: dayEvents.map<Widget>((ev) {
                  final start = DateTime.tryParse(ev['start_time'] ?? '');
                  final hhmm = start == null ? '' : DateFormat('HH:mm').format(start);
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Row(children: [
                      const Text('📌', style: TextStyle(fontSize: 14)),
                      const SizedBox(width: 8),
                      Expanded(child: Text('${ev['title']} · $hhmm',
                          style: const TextStyle(color: AppColors.cream, fontSize: 13))),
                      if (ev['formality'] != null)
                        ABadge(text: ev['formality'].toString().replaceAll('_', ' ')),
                    ]),
                  );
                }).toList(),
              ),
            ),

          if (rec == null)
            const Center(
              child: Padding(
                padding: EdgeInsets.symmetric(vertical: 20),
                child: Text('No outfit for this day yet. Generate the full week.',
                    style: TextStyle(color: AppColors.creamDim, fontSize: 13)),
              ),
            )
          else ...[
            if (rec['notes'] != null && (rec['notes'] as String).isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text('"${rec['notes']}"',
                    style: const TextStyle(color: AppColors.creamDim, fontSize: 14, fontStyle: FontStyle.italic)),
              ),

            ...items.map<Widget>((oi) {
              final name = oi['item_name']?.toString() ?? 'Item';
              final cat = oi['item_category']?.toString() ?? 'other';
              final brand = oi['item_brand']?.toString() ?? '';
              final liked = oi['liked'];
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: liked == true ? AppColors.sage.withValues(alpha: 0.1) :
                           liked == false ? AppColors.terra.withValues(alpha: 0.1) :
                           AppColors.surface2,
                    border: Border.all(color: AppColors.border),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(children: [
                    Text(_catIcons[cat] ?? '📦', style: const TextStyle(fontSize: 18)),
                    const SizedBox(width: 10),
                    Expanded(child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(name, style: const TextStyle(color: AppColors.cream, fontSize: 13, fontWeight: FontWeight.w500)),
                        if (brand.isNotEmpty)
                          Text(brand, style: const TextStyle(color: AppColors.creamDim, fontSize: 11)),
                      ],
                    )),
                  ]),
                ),
              );
            }),

            const SizedBox(height: 12),
            if (accepted == null)
              Row(children: [
                Expanded(child: OutlinedButton(
                  onPressed: () => onFeedback(rec['id'] as int, false),
                  child: const Text('Skip'),
                )),
                const SizedBox(width: 10),
                Expanded(child: ElevatedButton(
                  onPressed: () => onFeedback(rec['id'] as int, true),
                  child: const Text('Wearing this'),
                )),
              ]),
          ],
        ],
      ),
    );
  }

  String _shortDate(String dateStr) {
    final d = DateTime.tryParse(dateStr);
    return d == null ? dateStr : DateFormat('d MMM').format(d);
  }
}
