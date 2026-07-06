import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import '../api/api.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';
import '../widgets/place_autocomplete.dart';

class TripPlannerScreen extends StatefulWidget {
  const TripPlannerScreen({super.key});
  @override
  State<TripPlannerScreen> createState() => _TripPlannerScreenState();
}

class _TripPlannerScreenState extends State<TripPlannerScreen> {
  List<dynamic> _trips = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await itineraryApi.trips.list();
      setState(() {
        _trips = (data is Map ? data['results'] : data) as List? ?? [];
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _showCreate() async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: AppColors.surface1,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => const _CreateTripSheet(),
    );
    if (ok == true) _load();
  }

  Future<void> _delete(int id, {String? name}) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface1,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text(
          'Delete this trip?',
          style: TextStyle(
            color: AppColors.cream,
            fontSize: 18,
            fontWeight: FontWeight.w700,
          ),
        ),
        content: Text(
          name != null && name.isNotEmpty
              ? '"$name" will be permanently removed. This cannot be undone.'
              : 'This trip will be permanently removed. This cannot be undone.',
          style: const TextStyle(
            color: AppColors.creamDim,
            fontSize: 14,
            height: 1.4,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            style: TextButton.styleFrom(foregroundColor: AppColors.creamDim),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.danger,
              foregroundColor: AppColors.cream,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await itineraryApi.trips.delete(id);
      if (!mounted) return;
      setState(() => _trips.removeWhere((t) => t['id'] == id));
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('Failed to delete trip: $e')),
      );
    }
  }

  Future<void> _recommend(Map<String, dynamic> trip) async {
    final messenger = ScaffoldMessenger.of(context);
    Map<String, dynamic>? output;
    String? error;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(
        child: CircularProgressIndicator(color: AppColors.terra),
      ),
    );
    try {
      final rawCities = trip['cities'];
      final cityList = rawCities is List
          ? rawCities
                .map((c) => c.toString())
                .where((s) => s.isNotEmpty)
                .toList()
          : <String>[];
      final payload = <String, dynamic>{
        'destination': trip['destination'],
        'start_date': trip['start_date'],
        'end_date': trip['end_date'],
        'occasion': 'travel',
      };
      final country = (trip['country'] ?? '').toString().trim();
      if (country.isNotEmpty) payload['country'] = country;
      if (cityList.isNotEmpty) payload['cities'] = cityList;
      final result = await agentsApi.smartRecommend(payload) as Map;
      final rawOutput = result['output'] ?? result;
      output = Map<String, dynamic>.from(rawOutput as Map);
    } catch (e) {
      error = e.toString();
    }
    if (!mounted) return;
    Navigator.of(context, rootNavigator: true).pop();
    if (error != null) {
      messenger.showSnackBar(SnackBar(content: Text(error)));
      return;
    }
    _showRecommendationSheet(trip, output!, isSaved: false);
  }

  void _showTripDetail(Map<String, dynamic> trip) {
    final saved = trip['saved_recommendation'];
    final savedMap = saved is Map ? Map<String, dynamic>.from(saved) : null;
    final height = MediaQuery.of(context).size.height * 0.88;
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface1,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => SizedBox(
        height: height,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      trip['name'] ?? trip['destination'] ?? '',
                      style: const TextStyle(
                        color: AppColors.cream,
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Home',
                    onPressed: () {
                      Navigator.pop(context);
                      context.go('/');
                    },
                    icon: const Icon(
                      Icons.home_outlined,
                      color: AppColors.cream,
                    ),
                  ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close, color: AppColors.cream),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                '📍 ${_tripLocationLabel(trip)}',
                style: const TextStyle(color: AppColors.creamDim, fontSize: 14),
              ),
              const SizedBox(height: 2),
              Text(
                '${_formatDate(trip['start_date'])} → ${_formatDate(trip['end_date'])}',
                style: const TextStyle(color: AppColors.creamDim, fontSize: 14),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: ListView(
                  children: [
                    if ((trip['notes'] ?? '').toString().isNotEmpty) ...[
                      ACard(
                        child: Text(
                          trip['notes'],
                          style: const TextStyle(
                            color: AppColors.cream,
                            fontSize: 13,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                    ],
                    if (savedMap != null) ...[
                      Row(
                        children: [
                          const Expanded(
                            child: Text(
                              'AI Outfit Recommendations',
                              style: TextStyle(
                                color: AppColors.cream,
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          const ABadge(
                            text: 'Saved',
                            variant: BadgeVariant.sage,
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      ..._savedRecommendationPreview(context, savedMap),
                    ] else
                      const EmptyState(
                        icon: '✨',
                        title: 'No recommendations yet',
                        body:
                            'Tap the button below to generate outfit ideas for this trip.',
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 10),
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.pop(context);
                  _recommend(trip);
                },
                icon: const Icon(Icons.auto_awesome, size: 16),
                label: Text(
                  savedMap != null
                      ? 'Refresh outfit recommendations'
                      : 'Get AI outfit recommendations',
                ),
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: () {
                  Navigator.pop(context);
                  _delete(trip['id'] as int, name: trip['name']?.toString());
                },
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.danger,
                ),
                icon: const Icon(Icons.delete_outline, size: 18),
                label: const Text('Delete trip'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showRecommendationSheet(
    Map<String, dynamic> trip,
    Map<String, dynamic> output, {
    required bool isSaved,
  }) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface1,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => _RecommendationSheet(
        trip: trip,
        output: output,
        isSaved: isSaved,
        onSaved: (saved) {
          setState(() {
            final idx = _trips.indexWhere((t) => t['id'] == trip['id']);
            if (idx >= 0)
              _trips[idx] = {
                ..._trips[idx],
                'saved_recommendation': saved ? output : null,
              };
          });
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.midnight,
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.terra,
        onPressed: _showCreate,
        child: const Icon(Icons.add),
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.terra),
            )
          : RefreshIndicator(
              color: AppColors.terra,
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  const Text(
                    'Trips',
                    style: TextStyle(
                      color: AppColors.cream,
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Plan your packing and daily looks.',
                    style: TextStyle(color: AppColors.creamDim, fontSize: 14),
                  ),
                  const SizedBox(height: 16),
                  GestureDetector(
                    onTap: () => context.go('/packing'),
                    child: ACard(
                      padding: const EdgeInsets.all(16),
                      background: AppColors.terraDim,
                      child: Row(
                        children: [
                          const Text('🎒', style: TextStyle(fontSize: 24)),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: const [
                                Text(
                                  'Pack by bag size',
                                  style: TextStyle(
                                    color: AppColors.cream,
                                    fontSize: 15,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                SizedBox(height: 2),
                                Text(
                                  'Fit a capsule to your backpack or carry-on.',
                                  style: TextStyle(
                                    color: AppColors.creamDim,
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Icon(
                            Icons.chevron_right,
                            color: AppColors.creamDim,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (_error != null) AlertBanner(message: _error!),
                  if (_trips.isEmpty)
                    const EmptyState(
                      icon: '✈',
                      title: 'No trips yet',
                      body: 'Plan your first trip with the + button.',
                    ),
                  for (final trip in _trips)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(14),
                        onTap: () =>
                            _showTripDetail(Map<String, dynamic>.from(trip)),
                        child: ACard(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      trip['name'] ?? trip['destination'] ?? '',
                                      style: const TextStyle(
                                        color: AppColors.cream,
                                        fontSize: 17,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ),
                                  if (trip['is_collaborative'] == true)
                                    Padding(
                                      padding: const EdgeInsets.only(right: 4),
                                      child: ABadge(
                                        text:
                                            trip['shared_wardrobe_name']
                                                ?.toString() ??
                                            'Shared',
                                        variant: BadgeVariant.terra,
                                      ),
                                    ),
                                  IconButton(
                                    onPressed: () => _delete(
                                      trip['id'] as int,
                                      name: trip['name']?.toString(),
                                    ),
                                    icon: const Icon(
                                      Icons.delete_outline,
                                      color: AppColors.danger,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '📍 ${_tripLocationLabel(Map<String, dynamic>.from(trip))}',
                                style: const TextStyle(
                                  color: AppColors.creamDim,
                                  fontSize: 13,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                '${_formatDate(trip['start_date'])} → ${_formatDate(trip['end_date'])}',
                                style: const TextStyle(
                                  color: AppColors.creamDim,
                                  fontSize: 13,
                                ),
                              ),
                              const SizedBox(height: 12),
                              Row(
                                children: [
                                  Expanded(
                                    child: ElevatedButton.icon(
                                      onPressed: () => _recommend(
                                        Map<String, dynamic>.from(trip),
                                      ),
                                      icon: const Icon(
                                        Icons.auto_awesome,
                                        size: 16,
                                      ),
                                      label: Text(
                                        trip['saved_recommendation'] != null
                                            ? 'Refresh outfits'
                                            : 'Recommend outfits',
                                      ),
                                    ),
                                  ),
                                  if (trip['saved_recommendation'] != null) ...[
                                    const SizedBox(width: 8),
                                    OutlinedButton(
                                      onPressed: () => _showRecommendationSheet(
                                        Map<String, dynamic>.from(trip),
                                        Map<String, dynamic>.from(
                                          trip['saved_recommendation'] as Map,
                                        ),
                                        isSaved: true,
                                      ),
                                      child: const Text('View'),
                                    ),
                                  ],
                                ],
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

  String _formatDate(dynamic d) {
    if (d == null) return '—';
    final dt = DateTime.tryParse(d.toString());
    return dt == null ? d.toString() : DateFormat('d MMM y').format(dt);
  }
}

class _CreateTripSheet extends StatefulWidget {
  const _CreateTripSheet();
  @override
  State<_CreateTripSheet> createState() => _CreateTripSheetState();
}

class _CreateTripSheetState extends State<_CreateTripSheet> {
  final _name = TextEditingController();
  final _country = TextEditingController();
  final _cityDraft = TextEditingController();
  String? _countryCode;
  final List<String> _cities = [];
  DateTime? _start;
  DateTime? _end;
  bool _saving = false;
  String? _error;
  List<dynamic> _wardrobes = [];
  int? _selectedWardrobe;

  @override
  void initState() {
    super.initState();
    _country.addListener(() {
      if (_country.text.trim().isEmpty && _countryCode != null) {
        setState(() => _countryCode = null);
      }
    });
    sharedWardrobesApi
        .list()
        .then((data) {
          final list = (data is Map ? data['results'] : data) as List? ?? [];
          if (mounted) setState(() => _wardrobes = list);
        })
        .catchError((_) {});
  }

  @override
  void dispose() {
    _name.dispose();
    _country.dispose();
    _cityDraft.dispose();
    super.dispose();
  }

  void _addCity(String c) {
    final trimmed = c.trim();
    if (trimmed.isEmpty || _cities.contains(trimmed)) return;
    setState(() => _cities.add(trimmed));
  }

  Future<void> _pickDate(bool isStart) async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: (isStart ? _start : _end) ?? now,
      firstDate: now.subtract(const Duration(days: 30)),
      lastDate: now.add(const Duration(days: 365 * 3)),
    );
    if (picked != null)
      setState(() => isStart ? _start = picked : _end = picked);
  }

  Future<void> _save() async {
    final country = _country.text.trim();
    if (country.isEmpty || _cities.isEmpty || _start == null || _end == null) {
      setState(
        () => _error = 'Country, at least one city, and dates are required.',
      );
      return;
    }
    final destination = [..._cities, country].join(', ');
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await itineraryApi.trips.create({
        'name': _name.text.trim().isEmpty ? destination : _name.text.trim(),
        'destination': destination,
        'country': country,
        'cities': _cities,
        'start_date': DateFormat('yyyy-MM-dd').format(_start!),
        'end_date': DateFormat('yyyy-MM-dd').format(_end!),
        if (_selectedWardrobe != null) 'shared_wardrobe': _selectedWardrobe,
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      setState(() {
        _saving = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Plan a trip',
              style: TextStyle(
                color: AppColors.cream,
                fontSize: 20,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 16),
            if (_error != null) AlertBanner(message: _error!),
            LabeledInput(
              label: 'Name (optional)',
              controller: _name,
              hint: 'Lisbon getaway',
            ),
            PlaceAutocompleteField(
              label: 'Country',
              controller: _country,
              hint: 'e.g. Portugal',
              mode: PlaceMode.country,
              onSelected: (p) => setState(() => _countryCode = p.countryCode),
            ),
            PlaceAutocompleteField(
              label: 'Cities',
              controller: _cityDraft,
              hint: 'Type a city and select…',
              mode: PlaceMode.city,
              countryCode: _countryCode,
              disabled: _country.text.trim().isEmpty,
              disabledHint: 'Select a country first',
              onSelected: (p) {
                _addCity(p.name);
                _cityDraft.clear();
              },
            ),
            if (_cities.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: _cities
                      .map(
                        (c) => InputChip(
                          label: Text(
                            c,
                            style: const TextStyle(
                              color: AppColors.cream,
                              fontSize: 12,
                            ),
                          ),
                          backgroundColor: AppColors.surface2,
                          side: const BorderSide(color: AppColors.border),
                          deleteIconColor: AppColors.creamDim,
                          onDeleted: () => setState(() => _cities.remove(c)),
                        ),
                      )
                      .toList(),
                ),
              ),
            if (_wardrobes.isNotEmpty) ...[
              const Text(
                'SHARED WARDROBE',
                style: TextStyle(
                  color: AppColors.creamDim,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 6),
              DropdownButtonFormField<int?>(
                initialValue: _selectedWardrobe,
                dropdownColor: AppColors.surface1,
                style: const TextStyle(color: AppColors.cream),
                decoration: const InputDecoration(
                  enabledBorder: OutlineInputBorder(
                    borderSide: BorderSide(color: AppColors.border),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderSide: BorderSide(color: AppColors.terra),
                  ),
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 12,
                  ),
                ),
                items: [
                  const DropdownMenuItem<int?>(
                    value: null,
                    child: Text('None — personal trip'),
                  ),
                  for (final sw in _wardrobes)
                    DropdownMenuItem<int?>(
                      value: sw['id'] as int,
                      child: Text(
                        '${sw['name']} (${(sw['members'] as List?)?.length ?? 0} members)',
                      ),
                    ),
                ],
                onChanged: (v) => setState(() => _selectedWardrobe = v),
              ),
              const SizedBox(height: 8),
            ],
            Row(
              children: [
                Expanded(
                  child: _DateField(
                    label: 'Start',
                    value: _start,
                    onTap: () => _pickDate(true),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _DateField(
                    label: 'End',
                    value: _end,
                    onTap: () => _pickDate(false),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            APrimaryButton(
              label: 'Create trip',
              loading: _saving,
              onPressed: _save,
            ),
          ],
        ),
      ),
    );
  }
}

class _DateField extends StatelessWidget {
  final String label;
  final DateTime? value;
  final VoidCallback onTap;
  const _DateField({
    required this.label,
    required this.value,
    required this.onTap,
  });
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label.toUpperCase(),
          style: const TextStyle(
            color: AppColors.creamDim,
            fontSize: 11,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 6),
        GestureDetector(
          onTap: onTap,
          child: Container(
            height: 48,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            alignment: Alignment.centerLeft,
            decoration: BoxDecoration(
              color: AppColors.surface2,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.border),
            ),
            child: Text(
              value == null
                  ? 'Pick a date'
                  : DateFormat('d MMM y').format(value!),
              style: TextStyle(
                color: value == null ? AppColors.creamDim : AppColors.cream,
              ),
            ),
          ),
        ),
        const SizedBox(height: 14),
      ],
    );
  }
}

const Map<String, String> _roleIcon = {
  'top': '👕',
  'bottom': '👖',
  'outerwear': '🧥',
  'footwear': '👟',
  'accessory': '👜',
  'dress': '👗',
  'underwear': '🩲',
};

const Map<String, Map<String, dynamic>> _severityStyle = {
  'required': {'badge': BadgeVariant.terra, 'icon': '⚠'},
  'warning': {'badge': BadgeVariant.gold, 'icon': '⚡'},
  'info': {'badge': BadgeVariant.sky, 'icon': 'ℹ'},
};

String _tripLocationLabel(Map<String, dynamic> trip) {
  final raw = trip['cities'];
  final cities = raw is List
      ? raw.map((c) => c.toString()).where((s) => s.isNotEmpty).toList()
      : <String>[];
  final country = (trip['country'] ?? '').toString().trim();
  if (cities.isNotEmpty) {
    return country.isNotEmpty
        ? '${cities.join(', ')} · $country'
        : cities.join(', ');
  }
  return (trip['destination'] ?? '—').toString();
}

String _fmtDay(dynamic raw) {
  if (raw == null) return '';
  final dt = DateTime.tryParse(raw.toString());
  if (dt == null) return raw.toString();
  return DateFormat('EEE, MMM d').format(dt);
}

bool _isEstimatedWeather(Map? w) {
  final src = w?['source'];
  return src == 'climatology' || src == 'estimated';
}

String _weatherIcon(Map? w) {
  if (w == null) return '⛅';
  if (w['is_raining'] == true) return '🌧';
  if (w['is_cold'] == true) return '🧥';
  if (w['is_hot'] == true) return '☀';
  return '⛅';
}

Future<void> _openLink(String url) async {
  final uri = Uri.tryParse(url);
  if (uri != null) await launchUrl(uri, mode: LaunchMode.externalApplication);
}

class _Section {
  final String id, label, icon;
  final int count;
  final List<Widget> Function(Map<String, dynamic>) build;
  const _Section(this.id, this.label, this.icon, this.count, this.build);
}

List<_Section> _sectionsFor(Map<String, dynamic> o) {
  final cultural = (o['cultural'] is Map)
      ? Map<String, dynamic>.from(o['cultural'] as Map)
      : <String, dynamic>{};
  final days = (o['days'] as List?) ?? const [];
  final shopping = (o['shopping_suggestions'] as List?) ?? const [];
  final highlights = (cultural['highlights'] as List?) ?? const [];
  final rulesCount =
      ((cultural['rules'] as List?)?.length ?? 0) +
      ((cultural['events'] as List?)?.length ?? 0);
  final wardrobeMatches = (o['wardrobe_matches'] as List?) ?? const [];
  final outfitCount = days.isEmpty ? wardrobeMatches.length : days.length;
  final dressCode = cultural['overall_dress_code']?.toString() ?? '';
  return [
    _Section(
      'dress',
      'Dress Code',
      '🧭',
      dressCode.isNotEmpty ? 1 : 0,
      _dressCodeChildren,
    ),
    _Section('outfits', 'Outfit Plan', '👔', outfitCount, _outfitChildren),
    _Section(
      'shopping',
      'Items to Buy',
      '🛍',
      shopping.length,
      _shoppingChildren,
    ),
    _Section(
      'places',
      'Places to Visit',
      '📍',
      highlights.length,
      _placesChildren,
    ),
    _Section('culture', 'Cultural Guide', '📜', rulesCount, _cultureChildren),
  ];
}

List<Widget> _savedRecommendationPreview(
  BuildContext context,
  Map<String, dynamic> saved,
) {
  if (saved['multi_city'] == true && saved['cities'] is List) {
    final entries = (saved['cities'] as List).whereType<Map>().toList();
    final widgets = <Widget>[];
    for (final e in entries) {
      final city = e['city']?.toString() ?? '';
      final rec = (e['recommendation'] is Map)
          ? Map<String, dynamic>.from(e['recommendation'] as Map)
          : <String, dynamic>{};
      widgets
        ..add(
          Padding(
            padding: const EdgeInsets.only(top: 8, bottom: 6),
            child: Text(
              '📍 $city',
              style: const TextStyle(
                color: AppColors.cream,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        )
        ..addAll(buildRecommendationChildren(context, rec));
    }
    return widgets;
  }
  return buildRecommendationChildren(context, saved);
}

List<Widget> buildRecommendationChildren(
  BuildContext context,
  Map<String, dynamic> o,
) {
  final sections = _sectionsFor(o);
  return [
    for (final s in sections)
      Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: _SectionTile(section: s, output: o),
      ),
  ];
}

class _SectionTile extends StatelessWidget {
  final _Section section;
  final Map<String, dynamic> output;
  const _SectionTile({required this.section, required this.output});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => _SectionDetailPage(section: section, output: output),
        ),
      ),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surface1,
          border: Border.all(color: AppColors.border),
          borderRadius: BorderRadius.circular(14),
        ),
        padding: const EdgeInsets.fromLTRB(14, 14, 10, 14),
        child: Row(
          children: [
            Text(section.icon, style: const TextStyle(fontSize: 22)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                section.label,
                style: const TextStyle(
                  color: AppColors.cream,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            ABadge(text: '${section.count}', variant: BadgeVariant.sky),
            const SizedBox(width: 8),
            const Icon(
              Icons.chevron_right,
              color: AppColors.creamDim,
              size: 22,
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionDetailPage extends StatelessWidget {
  final _Section section;
  final Map<String, dynamic> output;
  const _SectionDetailPage({required this.section, required this.output});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.midnight,
      appBar: AppBar(
        backgroundColor: AppColors.surface1,
        foregroundColor: AppColors.cream,
        title: Row(
          children: [
            Text(section.icon, style: const TextStyle(fontSize: 20)),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                section.label,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [...section.build(output), const SizedBox(height: 40)],
      ),
    );
  }
}

List<Widget> _dressCodeChildren(Map<String, dynamic> o) {
  final cultural = (o['cultural'] is Map)
      ? Map<String, dynamic>.from(o['cultural'] as Map)
      : <String, dynamic>{};
  final dc = cultural['overall_dress_code']?.toString() ?? '';
  if (dc.isEmpty) {
    return const [
      EmptyState(
        icon: '🧭',
        title: 'No dress code info',
        body: 'The AI did not return a local dress code for this destination.',
      ),
    ];
  }
  return [
    Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface2,
        border: const Border(
          left: BorderSide(color: AppColors.terra, width: 3),
        ),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'LOCAL DRESS CODE',
            style: TextStyle(
              color: AppColors.creamDim,
              fontSize: 11,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            dc,
            style: const TextStyle(
              color: AppColors.cream,
              fontSize: 14,
              height: 1.5,
            ),
          ),
        ],
      ),
    ),
  ];
}

List<Widget> _outfitChildren(Map<String, dynamic> o) {
  final days = (o['days'] as List?) ?? const [];
  final wardrobeMatches = (o['wardrobe_matches'] as List?) ?? const [];
  final outfit = (o['outfit'] is Map)
      ? Map<String, dynamic>.from(o['outfit'] as Map)
      : <String, dynamic>{};
  if (days.isNotEmpty) {
    final hasEstimated = days.any((d) {
      final w = (d is Map) ? d['weather'] : null;
      return _isEstimatedWeather(
        w is Map ? Map<String, dynamic>.from(w) : null,
      );
    });
    return [
      for (final d in days) _DayCard(day: Map<String, dynamic>.from(d as Map)),
      if (hasEstimated)
        const Padding(
          padding: EdgeInsets.only(top: 4),
          child: Text.rich(
            TextSpan(
              style: TextStyle(
                color: AppColors.creamDim,
                fontSize: 11,
                fontStyle: FontStyle.italic,
              ),
              children: [
                TextSpan(
                  text: '*',
                  style: TextStyle(
                    color: AppColors.terraLight,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                TextSpan(
                  text:
                      ' Estimated from historical averages — live forecast not yet available for these dates.',
                ),
              ],
            ),
          ),
        ),
    ];
  }
  if (wardrobeMatches.isEmpty && (outfit['notes'] ?? '').toString().isEmpty) {
    return const [
      EmptyState(
        icon: '👔',
        title: 'No outfit data',
        body: 'No outfit suggestions were returned.',
      ),
    ];
  }
  return [
    if ((outfit['notes'] ?? '').toString().isNotEmpty)
      ACard(
        child: Text(
          outfit['notes'],
          style: const TextStyle(
            color: AppColors.cream,
            fontSize: 13,
            height: 1.4,
          ),
        ),
      ),
    for (final m in wardrobeMatches)
      _WardrobeMatchTile(match: Map<String, dynamic>.from(m as Map)),
  ];
}

List<Widget> _shoppingChildren(Map<String, dynamic> o) {
  final shopping = (o['shopping_suggestions'] as List?) ?? const [];
  if (shopping.isEmpty) {
    return const [
      EmptyState(
        icon: '✓',
        title: "You're all set!",
        body: 'Your wardrobe has everything you need for this trip.',
      ),
    ];
  }
  return [
    for (final s in shopping)
      _ShoppingCard(item: Map<String, dynamic>.from(s as Map)),
  ];
}

List<Widget> _placesChildren(Map<String, dynamic> o) {
  final cultural = (o['cultural'] is Map)
      ? Map<String, dynamic>.from(o['cultural'] as Map)
      : <String, dynamic>{};
  final highlights = (cultural['highlights'] as List?) ?? const [];
  if (highlights.isEmpty) {
    return const [
      EmptyState(
        icon: '📍',
        title: 'No places yet',
        body: "AI couldn't identify specific places for this destination.",
      ),
    ];
  }
  return [
    for (final h in highlights)
      _PlaceCard(place: Map<String, dynamic>.from(h as Map)),
  ];
}

List<Widget> _cultureChildren(Map<String, dynamic> o) {
  final cultural = (o['cultural'] is Map)
      ? Map<String, dynamic>.from(o['cultural'] as Map)
      : <String, dynamic>{};
  final rules = (cultural['rules'] as List?) ?? const [];
  final events = (cultural['events'] as List?) ?? const [];
  final tips = (cultural['general_tips'] as List?) ?? const [];
  if (rules.isEmpty && events.isEmpty && tips.isEmpty) {
    return const [
      EmptyState(
        icon: '📜',
        title: 'No cultural data',
        body: 'Check local dress codes before your trip.',
      ),
    ];
  }
  return [
    if (rules.isNotEmpty) ...[
      const Padding(
        padding: EdgeInsets.only(bottom: 8),
        child: Text(
          'Dress Code Rules',
          style: TextStyle(
            color: AppColors.cream,
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      for (final r in rules)
        _RuleCard(rule: Map<String, dynamic>.from(r as Map)),
    ],
    if (events.isNotEmpty) ...[
      const Padding(
        padding: EdgeInsets.only(top: 12, bottom: 8),
        child: Text(
          'Local Events',
          style: TextStyle(
            color: AppColors.cream,
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      for (final ev in events)
        _EventCard(event: Map<String, dynamic>.from(ev as Map)),
    ],
    if (tips.isNotEmpty) ...[
      const Padding(
        padding: EdgeInsets.only(top: 12, bottom: 8),
        child: Text(
          'General Tips',
          style: TextStyle(
            color: AppColors.cream,
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      for (final t in tips)
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.surface2,
              border: Border.all(color: AppColors.border),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '💡  ',
                  style: TextStyle(color: AppColors.terraLight, fontSize: 14),
                ),
                Expanded(
                  child: Text(
                    t.toString(),
                    style: const TextStyle(
                      color: AppColors.cream,
                      fontSize: 13,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
    ],
  ];
}

List<Widget> _buildPackingList(Map<String, dynamic> raw) {
  final summary = (raw['wardrobe_summary'] as List?) ?? const [];
  if (summary.isEmpty) {
    return const [
      EmptyState(
        icon: '🧳',
        title: 'No packing list',
        body: 'No wardrobe items were matched across cities.',
      ),
    ];
  }
  return [
    const Padding(
      padding: EdgeInsets.only(bottom: 12),
      child: Text(
        'Pack these items — each works across multiple destinations.',
        style: TextStyle(color: AppColors.creamDim, fontSize: 13),
      ),
    ),
    for (final m in summary)
      _WardrobeMatchTile(
        match: Map<String, dynamic>.from(m as Map),
        cities: (m['suitable_cities'] as List?)
            ?.map((c) => c.toString())
            .toList(),
      ),
  ];
}

class _WardrobeMatchTile extends StatelessWidget {
  final Map<String, dynamic> match;
  final List<String>? cities;
  const _WardrobeMatchTile({required this.match, this.cities});
  @override
  Widget build(BuildContext context) {
    final item = (match['item'] is Map)
        ? Map<String, dynamic>.from(match['item'] as Map)
        : <String, dynamic>{};
    final role = match['role']?.toString() ?? '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: ACard(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  _roleIcon[role] ?? '👔',
                  style: const TextStyle(fontSize: 20),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item['name']?.toString() ?? '—',
                        style: const TextStyle(
                          color: AppColors.cream,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        '${item['category'] ?? ''} · $role',
                        style: const TextStyle(
                          color: AppColors.creamDim,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
                const ABadge(text: 'owned', variant: BadgeVariant.sage),
              ],
            ),
            if (cities != null && cities!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: [
                  for (final c in cities!)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.terraDim,
                        borderRadius: BorderRadius.circular(100),
                      ),
                      child: Text(
                        '📍 $c',
                        style: const TextStyle(
                          color: AppColors.cream,
                          fontSize: 10,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ShoppingCard extends StatelessWidget {
  final Map<String, dynamic> item;
  const _ShoppingCard({required this.item});
  @override
  Widget build(BuildContext context) {
    final links = (item['links'] is Map)
        ? Map<String, dynamic>.from(item['links'] as Map)
        : <String, dynamic>{};
    final role = item['role']?.toString() ?? '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: ACard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  _roleIcon[role] ?? '🛍',
                  style: const TextStyle(fontSize: 22),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    item['name']?.toString() ??
                        item['description']?.toString() ??
                        '—',
                    style: const TextStyle(
                      color: AppColors.cream,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (item['price_range'] != null)
                  Text(
                    item['price_range'].toString(),
                    style: const TextStyle(
                      color: AppColors.terraLight,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
              ],
            ),
            if (item['brand'] != null) ...[
              const SizedBox(height: 4),
              Text(
                item['brand'].toString(),
                style: const TextStyle(color: AppColors.creamDim, fontSize: 11),
              ),
            ],
            if ((item['description'] ?? '').toString().isNotEmpty &&
                item['name'] != null) ...[
              const SizedBox(height: 6),
              Text(
                item['description'].toString(),
                style: const TextStyle(
                  color: AppColors.creamDim,
                  fontSize: 12,
                  height: 1.4,
                ),
              ),
            ],
            if ((item['why'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                item['why'].toString(),
                style: const TextStyle(
                  color: AppColors.terraLight,
                  fontSize: 11,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
            if (links.isNotEmpty) ...[
              const SizedBox(height: 10),
              const Divider(color: AppColors.border, height: 1),
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  if (links['google_shopping'] != null)
                    _LinkChip(
                      label: '🔗 Google Shopping',
                      url: links['google_shopping'].toString(),
                    ),
                  if (links['amazon'] != null)
                    _LinkChip(
                      label: '🔗 Amazon',
                      url: links['amazon'].toString(),
                    ),
                  if (links['asos'] != null)
                    _LinkChip(label: '🔗 ASOS', url: links['asos'].toString()),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _LinkChip extends StatelessWidget {
  final String label;
  final String url;
  const _LinkChip({required this.label, required this.url});
  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => _openLink(url),
      borderRadius: BorderRadius.circular(100),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          border: Border.all(color: AppColors.border),
          borderRadius: BorderRadius.circular(100),
        ),
        child: Text(
          label,
          style: const TextStyle(color: AppColors.cream, fontSize: 11),
        ),
      ),
    );
  }
}

class _PlaceCard extends StatelessWidget {
  final Map<String, dynamic> place;
  const _PlaceCard({required this.place});
  @override
  Widget build(BuildContext context) {
    final type = place['type']?.toString() ?? '';
    final icon = type == 'nature'
        ? '🌿'
        : type == 'restaurant'
        ? '🍽'
        : type == 'market'
        ? '🛒'
        : type == 'museum'
        ? '🏛'
        : '📍';
    final formality = place['formality']?.toString().replaceAll('_', ' ');
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: ACard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(icon, style: const TextStyle(fontSize: 20)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    place['name']?.toString() ?? '—',
                    style: const TextStyle(
                      color: AppColors.cream,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (formality != null && formality.isNotEmpty)
                  ABadge(text: formality, variant: BadgeVariant.sky),
              ],
            ),
            if ((place['description'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                place['description'].toString(),
                style: const TextStyle(
                  color: AppColors.creamDim,
                  fontSize: 12,
                  height: 1.4,
                ),
              ),
            ],
            if ((place['clothing_tip'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 10),
              const Divider(color: AppColors.border, height: 1),
              const SizedBox(height: 8),
              RichText(
                text: TextSpan(
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.cream,
                    height: 1.4,
                  ),
                  children: [
                    const TextSpan(
                      text: '👔 What to wear: ',
                      style: TextStyle(
                        color: AppColors.terraLight,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    TextSpan(text: place['clothing_tip'].toString()),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _RuleCard extends StatelessWidget {
  final Map<String, dynamic> rule;
  const _RuleCard({required this.rule});
  @override
  Widget build(BuildContext context) {
    final severity = rule['severity']?.toString() ?? 'info';
    final style = _severityStyle[severity] ?? _severityStyle['info']!;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: ACard(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(style['icon'] as String, style: const TextStyle(fontSize: 18)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      ABadge(
                        text: severity,
                        variant: style['badge'] as BadgeVariant,
                      ),
                      if (rule['type'] != null &&
                          rule['type'] != 'general') ...[
                        const SizedBox(width: 6),
                        Text(
                          rule['type'].toString().replaceAll('_', ' '),
                          style: const TextStyle(
                            color: AppColors.creamDim,
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    rule['description']?.toString() ?? '',
                    style: const TextStyle(
                      color: AppColors.cream,
                      fontSize: 12,
                      height: 1.4,
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

class _EventCard extends StatelessWidget {
  final Map<String, dynamic> event;
  const _EventCard({required this.event});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: ACard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('🎊 ', style: TextStyle(fontSize: 16)),
                Expanded(
                  child: Text(
                    event['name']?.toString() ?? '—',
                    style: const TextStyle(
                      color: AppColors.cream,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            if ((event['date_range'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                '📅 ${event['date_range']}',
                style: const TextStyle(
                  color: AppColors.terraLight,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
            if ((event['description'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                event['description'].toString(),
                style: const TextStyle(
                  color: AppColors.creamDim,
                  fontSize: 12,
                  height: 1.4,
                ),
              ),
            ],
            if ((event['clothing_note'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 8),
              const Divider(color: AppColors.border, height: 1),
              const SizedBox(height: 6),
              RichText(
                text: TextSpan(
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.cream,
                    height: 1.4,
                  ),
                  children: [
                    const TextSpan(
                      text: '👔 ',
                      style: TextStyle(
                        color: AppColors.terraLight,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    TextSpan(text: event['clothing_note'].toString()),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _RecommendationSheet extends StatefulWidget {
  final Map<String, dynamic> trip;
  final Map<String, dynamic> output;
  final bool isSaved;
  final void Function(bool saved) onSaved;
  const _RecommendationSheet({
    required this.trip,
    required this.output,
    required this.isSaved,
    required this.onSaved,
  });

  @override
  State<_RecommendationSheet> createState() => _RecommendationSheetState();
}

class _RecommendationSheetState extends State<_RecommendationSheet> {
  bool _saving = false;
  bool _saved = false;
  String? _error;
  int _cityIdx = 0;

  @override
  void initState() {
    super.initState();
    _saved = widget.isSaved;
  }

  Future<void> _save() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final result = await itineraryApi.trips.saveRecommendation(
        widget.trip['id'] as int,
        widget.output,
      );
      widget.onSaved(true);
      setState(() {
        _saving = false;
        _saved = true;
      });
      if (mounted && result is Map) {
        final added = result['shared_wardrobe_items_added'];
        if (added is int && added > 0) {
          final swName =
              widget.trip['shared_wardrobe_name']?.toString() ??
              'shared wardrobe';
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                '$added item${added > 1 ? 's' : ''} added to "$swName".',
              ),
            ),
          );
        }
      }
    } catch (e) {
      setState(() {
        _saving = false;
        _error = e.toString();
      });
    }
  }

  Future<void> _clear() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await itineraryApi.trips.clearRecommendation(widget.trip['id'] as int);
      widget.onSaved(false);
      if (mounted) Navigator.pop(context);
    } catch (e) {
      setState(() {
        _saving = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final raw = widget.output;
    final isMulti = raw['multi_city'] == true && raw['cities'] is List;
    final cityEntries = isMulti
        ? (raw['cities'] as List)
              .whereType<Map>()
              .map((m) => Map<String, dynamic>.from(m))
              .toList()
        : const <Map<String, dynamic>>[];
    if (isMulti && _cityIdx >= cityEntries.length) _cityIdx = 0;
    final o = isMulti && _cityIdx >= 0
        ? Map<String, dynamic>.from(
            (cityEntries[_cityIdx]['recommendation'] as Map?) ?? {},
          )
        : raw;
    final height = MediaQuery.of(context).size.height * 0.85;
    return SizedBox(
      height: height,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'AI Outfit Recommendations',
                    style: TextStyle(
                      color: AppColors.cream,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                IconButton(
                  tooltip: 'Home',
                  onPressed: () {
                    Navigator.pop(context);
                    context.go('/');
                  },
                  icon: const Icon(Icons.home_outlined, color: AppColors.cream),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close, color: AppColors.cream),
                ),
              ],
            ),
            Text(
              '${_tripLocationLabel(widget.trip)} · ${widget.trip['start_date']} → ${widget.trip['end_date']}',
              style: const TextStyle(color: AppColors.creamDim, fontSize: 12),
            ),
            const SizedBox(height: 12),
            if (_error != null) AlertBanner(message: _error!),
            if (isMulti) ...[
              SizedBox(
                height: 36,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: cityEntries.length + 1,
                  separatorBuilder: (_, _) => const SizedBox(width: 8),
                  itemBuilder: (_, i) {
                    final isPackingTab = i == cityEntries.length;
                    final active = isPackingTab
                        ? _cityIdx == -1
                        : i == _cityIdx;
                    return ChoiceChip(
                      label: Text(
                        isPackingTab
                            ? '🧳 Packing List'
                            : cityEntries[i]['city']?.toString() ?? '—',
                      ),
                      selected: active,
                      onSelected: (_) =>
                          setState(() => _cityIdx = isPackingTab ? -1 : i),
                      backgroundColor: AppColors.surface2,
                      selectedColor: AppColors.terra,
                      labelStyle: TextStyle(
                        color: active ? AppColors.cream : AppColors.creamDim,
                        fontSize: 12,
                        fontWeight: active ? FontWeight.w600 : FontWeight.w400,
                      ),
                      side: const BorderSide(color: AppColors.border),
                    );
                  },
                ),
              ),
              const SizedBox(height: 12),
            ],
            Expanded(
              child: _cityIdx == -1 && isMulti
                  ? ListView(children: _buildPackingList(raw))
                  : ListView(children: buildRecommendationChildren(context, o)),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                if (_saved)
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _saving ? null : _clear,
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.danger,
                      ),
                      child: Text(_saving ? 'Clearing…' : 'Clear saved'),
                    ),
                  )
                else
                  Expanded(
                    child: ElevatedButton(
                      onPressed: _saving ? null : _save,
                      child: Text(_saving ? 'Saving…' : 'Save to trip'),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _DayCard extends StatelessWidget {
  final Map<String, dynamic> day;
  const _DayCard({required this.day});
  @override
  Widget build(BuildContext context) {
    final w = (day['weather'] is Map)
        ? Map<String, dynamic>.from(day['weather'] as Map)
        : null;
    final matches = (day['wardrobe_matches'] as List?) ?? const [];
    final gaps = (day['gaps'] as List?) ?? const [];
    final dayNum = day['day']?.toString();
    final dateStr = _fmtDay(day['date']);
    final temp = w?['temp_c'];
    final feelsLike = w?['feels_like_c'];
    final precip = w?['precipitation_probability'];
    final wind = w?['wind_kmh'];
    final humidity = w?['humidity'];
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.surface2,
          border: Border.all(color: AppColors.border),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              children: [
                if (dayNum != null) ...[
                  Text(
                    'D$dayNum',
                    style: const TextStyle(
                      color: AppColors.terra,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(width: 10),
                ],
                Expanded(
                  child: Text(
                    dateStr,
                    style: const TextStyle(
                      color: AppColors.cream,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                Text(_weatherIcon(w), style: const TextStyle(fontSize: 16)),
                const SizedBox(width: 4),
                Text.rich(
                  TextSpan(
                    style: const TextStyle(
                      color: AppColors.creamDim,
                      fontSize: 11,
                    ),
                    children: [
                      TextSpan(
                        text:
                            '${temp != null ? '${temp.round()}°C' : '?'} · ${w?['condition'] ?? ''}',
                      ),
                      if (_isEstimatedWeather(w))
                        const TextSpan(
                          text: '*',
                          style: TextStyle(
                            color: AppColors.terraLight,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
            if (feelsLike != null &&
                temp != null &&
                (feelsLike - temp).abs() >= 2) ...[
              const SizedBox(height: 4),
              Text(
                'Feels like ${feelsLike.round()}°C',
                style: const TextStyle(
                  color: AppColors.terraLight,
                  fontSize: 11,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Wrap(
                spacing: 8,
                runSpacing: 4,
                children: [
                  if (precip is num && precip > 30)
                    ABadge(
                      text: '${precip.round()}% rain',
                      variant: BadgeVariant.sky,
                    ),
                  if (wind is num && wind > 20)
                    ABadge(
                      text: '💨 ${wind.round()} km/h',
                      variant: BadgeVariant.sky,
                    ),
                  if (humidity is num && humidity > 75)
                    ABadge(text: '💧 ${humidity}%', variant: BadgeVariant.sky),
                ],
              ),
            ),
            // Wardrobe matches for this day
            if (matches.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text(
                'FROM YOUR WARDROBE',
                style: TextStyle(
                  color: AppColors.creamDim,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 6),
              for (final m in matches)
                _WardrobeMatchTile(match: Map<String, dynamic>.from(m as Map)),
            ],
            // Gaps
            if (gaps.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                matches.isNotEmpty ? 'MISSING ITEMS' : 'ITEMS NEEDED',
                style: const TextStyle(
                  color: AppColors.terraLight,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final g in gaps)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0x1AE0A458),
                        border: Border.all(color: const Color(0x40E0A458)),
                        borderRadius: BorderRadius.circular(100),
                      ),
                      child: Text(
                        (g is Map
                                ? g['description']?.toString()
                                : g.toString()) ??
                            '',
                        style: const TextStyle(
                          color: Color(0xFFE0A458),
                          fontSize: 11,
                        ),
                      ),
                    ),
                ],
              ),
            ],
            if (matches.isEmpty && gaps.isEmpty) ...[
              const SizedBox(height: 8),
              const Text(
                'No specific outfit items for this day',
                style: TextStyle(
                  color: AppColors.creamDim,
                  fontSize: 11,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
