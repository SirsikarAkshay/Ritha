import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../api/api.dart';
import '../theme/app_theme.dart';
import '../widgets/ui.dart';
import '../widgets/place_autocomplete.dart';

const _popular = ['Japan', 'Turkey', 'India', 'Italy', 'Morocco', 'Thailand', 'Saudi Arabia'];

const _ruleIcons = {
  'cover_head':      '🧕',
  'cover_shoulders': '👘',
  'cover_knees':     '👖',
  'remove_shoes':    '👟',
  'modest_dress':    '🎀',
  'no_bare_feet':    '🦶',
  'festival_wear':   '🎊',
  'color_warning':   '🎨',
  'general':         '📝',
};

const _catIcons = {
  'top': '👕', 'bottom': '👖', 'dress': '👗', 'outerwear': '🧥',
  'footwear': '👟', 'accessory': '💍', 'activewear': '🏃', 'formal': '🤵', 'other': '📦',
};

class CulturalScreen extends StatefulWidget {
  const CulturalScreen({super.key});
  @override
  State<CulturalScreen> createState() => _CulturalScreenState();
}

class _CulturalScreenState extends State<CulturalScreen> {
  final _country = TextEditingController();
  final _city = TextEditingController();
  String _countryCode = '';
  List<dynamic>? _rules;
  List<dynamic> _events = [];
  Map<String, dynamic>? _advice;
  bool _loading = false;
  String? _error;
  String _activeTab = 'etiquette';

  @override
  void initState() {
    super.initState();
    _country.addListener(_onCountryTyped);
  }

  void _onCountryTyped() {
    // Any manual edit clears the locked country code until the user picks
    // a suggestion again — keeps the city filter honest.
    if (_countryCode.isNotEmpty) setState(() => _countryCode = '');
  }

  @override
  void dispose() {
    _country.removeListener(_onCountryTyped);
    _country.dispose();
    _city.dispose();
    super.dispose();
  }

  Future<void> _getAdvice() async {
    if (_country.text.trim().isEmpty) return;
    setState(() { _loading = true; _error = null; _advice = null; _activeTab = 'etiquette'; });
    try {
      final result = await agentsApi.culturalAdvisor({
        'country': _country.text.trim(),
        'city': _city.text.trim(),
      }) as Map;
      if (!mounted) return;
      if (result['status'] == 'completed') {
        final out = Map<String, dynamic>.from(result['output'] ?? {});
        setState(() {
          _advice = out;
          _rules = (out['rules'] is List) ? out['rules'] as List : [];
          _events = (out['local_events'] is List) ? out['local_events'] as List : [];
          _loading = false;
        });
      } else {
        setState(() {
          _error = (result['error'] ?? 'AI advisor failed').toString();
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  void _selectPopular(String c) {
    _country.text = c;
    _city.clear();
    setState(() => _countryCode = '');
  }

  @override
  Widget build(BuildContext context) {
    final highlights = (_advice?['highlights'] as List?) ?? const [];
    final placeHighlights = highlights.where((h) => (h is Map) && h['type'] != 'event').toList();
    final eventHighlights = highlights.where((h) => (h is Map) && h['type'] == 'event').toList();
    final matches = (_advice?['wardrobe_matches'] as List?) ?? const [];
    final gaps = (_advice?['gaps'] as List?) ?? const [];
    final wardrobeCount = matches.length + gaps.length;
    final eventsCount = eventHighlights.length + _events.length;

    final tabs = [
      _TabDef('etiquette', 'Etiquette', '📜', _rules?.length ?? 0),
      _TabDef('places',    'Places',    '📍', placeHighlights.length),
      _TabDef('events',    'Events',    '🎊', eventsCount),
      _TabDef('wardrobe',  'Wardrobe',  '👔', wardrobeCount),
    ];

    return Scaffold(
      backgroundColor: AppColors.midnight,
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text('Cultural Guide',
              style: TextStyle(color: AppColors.cream, fontSize: 28, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          const Text('Etiquette, events, and clothing advice for your destination.',
              style: TextStyle(color: AppColors.creamDim, fontSize: 14)),
          const SizedBox(height: 20),
          // Popular chips — above the input so the autocomplete dropdown
          // expands downward into empty space without overlapping them.
          const Padding(
            padding: EdgeInsets.only(bottom: 8),
            child: Text('POPULAR',
                style: TextStyle(
                  color: AppColors.creamDim,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.8,
                )),
          ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [for (final c in _popular) _PopularChip(label: c, onTap: () => _selectPopular(c))],
          ),
          const SizedBox(height: 20),
          Row(children: [
            Expanded(
              child: PlaceAutocompleteField(
                label: 'Country',
                hint: 'e.g. Turkey',
                controller: _country,
                mode: PlaceMode.country,
                onSelected: (p) {
                  setState(() => _countryCode = p.countryCode ?? '');
                  _city.clear();
                },
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: PlaceAutocompleteField(
                label: 'City (optional)',
                controller: _city,
                mode: PlaceMode.city,
                countryCode: _countryCode,
                disabled: _countryCode.isEmpty,
                disabledHint: 'Pick a country first',
                onSelected: (p) => _city.text = p.name,
              ),
            ),
          ]),
          APrimaryButton(label: '✦ Get Cultural Guide', loading: _loading, onPressed: _getAdvice),
          const SizedBox(height: 20),
          if (_error != null) AlertBanner(message: _error!),
          if (_advice != null) _AdviceCard(advice: _advice!, country: _country.text.trim(), city: _city.text.trim()),
          if (_rules == null && !_loading)
            const EmptyState(icon: '🌍', title: 'Pick a destination', body: 'Enter a country above and tap Get Cultural Guide for etiquette, events, places, and wardrobe advice.'),
          if (_rules != null) ...[
            _TabBar(tabs: tabs, active: _activeTab, onTap: (id) => setState(() => _activeTab = id)),
            const SizedBox(height: 16),
            if (_activeTab == 'etiquette') _etiquetteTab(),
            if (_activeTab == 'places')    _placesTab(placeHighlights),
            if (_activeTab == 'events')    _eventsTab(eventHighlights),
            if (_activeTab == 'wardrobe')  _wardrobeTab(matches, gaps),
          ],
        ],
      ),
    );
  }

  Widget _etiquetteTab() {
    if ((_rules ?? []).isEmpty) {
      return const EmptyState(icon: '📜', title: 'No etiquette rules found', body: 'Try a different destination.');
    }
    return Column(
      children: [
        for (final r in _rules!)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _RuleCard(rule: Map<String, dynamic>.from(r as Map)),
          ),
      ],
    );
  }

  Widget _placesTab(List places) {
    if (places.isEmpty) {
      return const EmptyState(icon: '📍', title: 'No places yet', body: 'Try a different destination.');
    }
    return Column(
      children: [
        for (final h in places)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _HighlightCard(data: Map<String, dynamic>.from(h as Map), isEvent: false),
          ),
      ],
    );
  }

  Widget _eventsTab(List eventHighlights) {
    if (eventHighlights.isEmpty && _events.isEmpty) {
      return const EmptyState(icon: '🎊', title: 'No events found', body: 'Nothing notable this month for this destination.');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (eventHighlights.isNotEmpty) ...[
          const Padding(
            padding: EdgeInsets.only(bottom: 12),
            child: Text('Upcoming, with clothing guidance',
                style: TextStyle(color: AppColors.creamDim, fontSize: 13)),
          ),
          for (final h in eventHighlights)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _HighlightCard(data: Map<String, dynamic>.from(h as Map), isEvent: true),
            ),
          const SizedBox(height: 12),
        ],
        if (_events.isNotEmpty) ...[
          const CardLabel('Events this month'),
          const SizedBox(height: 10),
          for (final e in _events)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _MonthlyEventCard(event: Map<String, dynamic>.from(e as Map)),
            ),
        ],
      ],
    );
  }

  Widget _wardrobeTab(List matches, List gaps) {
    if (matches.isEmpty && gaps.isEmpty) {
      return const EmptyState(icon: '👔', title: 'No wardrobe advice yet', body: 'Add items to your wardrobe to see matches and gaps for this destination.');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (matches.isNotEmpty) ...[
          const CardLabel('From your wardrobe'),
          const SizedBox(height: 10),
          for (final m in matches)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _MatchCard(match: Map<String, dynamic>.from(m as Map)),
            ),
          const SizedBox(height: 12),
        ],
        if (gaps.isNotEmpty) ...[
          const CardLabel('Missing from your wardrobe'),
          const SizedBox(height: 10),
          for (final g in gaps)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _GapCard(gap: Map<String, dynamic>.from(g as Map)),
            ),
        ],
      ],
    );
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────────

class _TabDef {
  final String id, label, icon;
  final int count;
  _TabDef(this.id, this.label, this.icon, this.count);
}

class _TabBar extends StatelessWidget {
  final List<_TabDef> tabs;
  final String active;
  final ValueChanged<String> onTap;
  const _TabBar({required this.tabs, required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const Border(bottom: BorderSide(color: AppColors.border)).toBoxDecoration(),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            for (final t in tabs)
              GestureDetector(
                onTap: () => onTap(t.id),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    border: Border(
                      bottom: BorderSide(
                        color: active == t.id ? AppColors.terraLight : Colors.transparent,
                        width: 2,
                      ),
                    ),
                  ),
                  child: Row(
                    children: [
                      Text(t.icon, style: const TextStyle(fontSize: 14)),
                      const SizedBox(width: 6),
                      Text(
                        t.label,
                        style: TextStyle(
                          color: active == t.id ? AppColors.cream : AppColors.creamDim,
                          fontSize: 13,
                          fontWeight: active == t.id ? FontWeight.w500 : FontWeight.w400,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppColors.surface3,
                          borderRadius: BorderRadius.circular(100),
                        ),
                        child: Text('${t.count}',
                            style: const TextStyle(color: AppColors.creamDim, fontSize: 10)),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

extension on Border {
  BoxDecoration toBoxDecoration() => BoxDecoration(border: this);
}

class _PopularChip extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  const _PopularChip({required this.label, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.surface2,
          borderRadius: BorderRadius.circular(100),
          border: Border.all(color: AppColors.border),
        ),
        child: Text(label, style: const TextStyle(color: AppColors.cream, fontSize: 12)),
      ),
    );
  }
}

class _AdviceCard extends StatelessWidget {
  final Map<String, dynamic> advice;
  final String country;
  final String city;
  const _AdviceCard({required this.advice, required this.country, required this.city});

  @override
  Widget build(BuildContext context) {
    final summary = advice['summary']?.toString() ?? '';
    final source = advice['source']?.toString();
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: ACard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Text('✦', style: TextStyle(fontSize: 20, color: AppColors.terraLight)),
              const SizedBox(width: 8),
              const CardLabel('AI Cultural Advisor'),
              if (source == 'ai') ...[
                const SizedBox(width: 8),
                const Text('· AI-generated',
                    style: TextStyle(color: AppColors.terraLight, fontSize: 10, letterSpacing: 0.5)),
              ],
            ]),
            const SizedBox(height: 10),
            Text(
              'Clothing guide for $country${city.isNotEmpty ? ', $city' : ''}',
              style: const TextStyle(color: AppColors.cream, fontSize: 16, fontWeight: FontWeight.w600),
            ),
            if (summary.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(summary, style: const TextStyle(color: AppColors.creamDim, fontSize: 13, height: 1.5)),
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
    final ruleType = rule['rule_type']?.toString() ?? 'general';
    final placeName = rule['place_name']?.toString();
    final description = rule['description']?.toString() ?? '';

    BadgeVariant sevVariant;
    String sevIcon;
    switch (severity) {
      case 'required': sevVariant = BadgeVariant.terra; sevIcon = '⚠'; break;
      case 'warning':  sevVariant = BadgeVariant.gold;  sevIcon = '⚡'; break;
      default:         sevVariant = BadgeVariant.sky;   sevIcon = 'ℹ';
    }

    return ACard(
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(_ruleIcons[ruleType] ?? '📝', style: const TextStyle(fontSize: 22)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    if (placeName != null && placeName.isNotEmpty)
                      Text(placeName,
                          style: const TextStyle(color: AppColors.cream, fontSize: 13, fontWeight: FontWeight.w600)),
                    ABadge(text: '$sevIcon $severity', variant: sevVariant),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                      decoration: BoxDecoration(color: AppColors.surface3, borderRadius: BorderRadius.circular(100)),
                      child: Text(ruleType.replaceAll('_', ' '),
                          style: const TextStyle(color: AppColors.creamDim, fontSize: 11)),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(description,
                    style: const TextStyle(color: AppColors.creamDim, fontSize: 13, height: 1.4)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _HighlightCard extends StatelessWidget {
  final Map<String, dynamic> data;
  final bool isEvent;
  const _HighlightCard({required this.data, required this.isEvent});

  @override
  Widget build(BuildContext context) {
    final name = data['name']?.toString() ?? '';
    final when = data['when']?.toString();
    final description = data['description']?.toString();
    final clothing = data['clothing']?.toString();
    final formality = data['formality']?.toString();

    return ACard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text(isEvent ? '🎊' : '📍', style: const TextStyle(fontSize: 18)),
            const SizedBox(width: 8),
            Expanded(
              child: Text(name,
                  style: const TextStyle(color: AppColors.cream, fontSize: 15, fontWeight: FontWeight.w600)),
            ),
            ABadge(text: isEvent ? 'EVENT' : 'PLACE', variant: isEvent ? BadgeVariant.gold : BadgeVariant.sky),
          ]),
          if (when != null && when.isNotEmpty && when != 'year-round') ...[
            const SizedBox(height: 6),
            Text('📅 $when',
                style: const TextStyle(color: AppColors.terraLight, fontSize: 12, fontWeight: FontWeight.w500)),
          ],
          if (description != null && description.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(description, style: const TextStyle(color: AppColors.creamDim, fontSize: 13, height: 1.4)),
          ],
          if (clothing != null && clothing.isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.only(top: 10),
              decoration: const BoxDecoration(border: Border(top: BorderSide(color: AppColors.border))),
              child: RichText(
                text: TextSpan(
                  style: const TextStyle(color: AppColors.cream, fontSize: 13, height: 1.4),
                  children: [
                    const TextSpan(text: '👔 What to wear: ',
                        style: TextStyle(color: AppColors.terraLight, fontWeight: FontWeight.w500)),
                    TextSpan(text: clothing),
                  ],
                ),
              ),
            ),
          ],
          if (formality != null && formality.isNotEmpty) ...[
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerLeft,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                decoration: BoxDecoration(color: AppColors.surface3, borderRadius: BorderRadius.circular(100)),
                child: Text(formality.replaceAll('_', ' '),
                    style: const TextStyle(color: AppColors.creamDim, fontSize: 11)),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _MonthlyEventCard extends StatelessWidget {
  final Map<String, dynamic> event;
  const _MonthlyEventCard({required this.event});

  @override
  Widget build(BuildContext context) {
    final name = event['name']?.toString() ?? '';
    final description = event['description']?.toString() ?? '';
    final clothingNote = event['clothing_note']?.toString();

    return ACard(
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('🎊', style: TextStyle(fontSize: 22)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name,
                    style: const TextStyle(color: AppColors.cream, fontSize: 15, fontWeight: FontWeight.w600)),
                if (description.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(description,
                      style: const TextStyle(color: AppColors.creamDim, fontSize: 13, height: 1.4)),
                ],
                if (clothingNote != null && clothingNote.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppColors.goldDim,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text('👔 $clothingNote',
                        style: const TextStyle(color: AppColors.gold, fontSize: 12, height: 1.4)),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _MatchCard extends StatelessWidget {
  final Map<String, dynamic> match;
  const _MatchCard({required this.match});

  @override
  Widget build(BuildContext context) {
    final category = match['category']?.toString() ?? 'other';
    final name = match['name']?.toString() ?? '';
    final reason = match['reason']?.toString() ?? '';
    return ACard(
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(_catIcons[category] ?? '📦', style: const TextStyle(fontSize: 22)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name,
                    style: const TextStyle(color: AppColors.cream, fontSize: 14, fontWeight: FontWeight.w600)),
                if (reason.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(reason,
                      style: const TextStyle(color: AppColors.creamDim, fontSize: 12, height: 1.4)),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GapCard extends StatelessWidget {
  final Map<String, dynamic> gap;
  const _GapCard({required this.gap});

  @override
  Widget build(BuildContext context) {
    final category = gap['category']?.toString() ?? 'other';
    final description = gap['description']?.toString() ?? '';
    final why = gap['why']?.toString();
    final links = (gap['search_links'] as List?) ?? const [];

    return ACard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(_catIcons[category] ?? '🛍', style: const TextStyle(fontSize: 22)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(description,
                      style: const TextStyle(color: AppColors.cream, fontSize: 14, fontWeight: FontWeight.w600)),
                  if (why != null && why.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(why,
                        style: const TextStyle(color: AppColors.creamDim, fontSize: 12, height: 1.4)),
                  ],
                ],
              ),
            ),
          ]),
          if (links.isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.only(top: 10),
              decoration: const BoxDecoration(border: Border(top: BorderSide(color: AppColors.border))),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final link in links)
                    if (link is Map)
                      _LinkChip(
                        label: link['label']?.toString() ?? 'Shop',
                        url: link['url']?.toString() ?? '',
                      ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _LinkChip extends StatelessWidget {
  final String label;
  final String url;
  const _LinkChip({required this.label, required this.url});

  Future<void> _open() async {
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: _open,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(100),
          border: Border.all(color: AppColors.border),
        ),
        child: Text('🔗 $label',
            style: const TextStyle(color: AppColors.cream, fontSize: 12)),
      ),
    );
  }
}
