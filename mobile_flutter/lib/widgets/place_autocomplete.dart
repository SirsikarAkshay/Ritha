import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../theme/app_theme.dart';

// Open-Meteo geocoding — free, no API key required.
const _geocodeBase = 'https://geocoding-api.open-meteo.com/v1/search';

enum PlaceMode { any, country, city }

class PlaceSuggestion {
  final String name;
  final String? admin1;
  final String? country;
  final String? countryCode;
  final String? featureCode;
  final double? latitude;
  final double? longitude;

  PlaceSuggestion({
    required this.name,
    this.admin1,
    this.country,
    this.countryCode,
    this.featureCode,
    this.latitude,
    this.longitude,
  });

  factory PlaceSuggestion.fromJson(Map<String, dynamic> json) =>
      PlaceSuggestion(
        name: (json['name'] ?? '').toString(),
        admin1: json['admin1']?.toString(),
        country: json['country']?.toString(),
        countryCode: json['country_code']?.toString(),
        featureCode: json['feature_code']?.toString(),
        latitude: (json['latitude'] as num?)?.toDouble(),
        longitude: (json['longitude'] as num?)?.toDouble(),
      );

  String labelFor(PlaceMode mode) {
    if (mode == PlaceMode.country)
      return (country != null && country!.isNotEmpty) ? country! : name;
    return [
      name,
      admin1,
      country,
    ].where((s) => s != null && s.isNotEmpty).join(', ');
  }

  String get label => labelFor(PlaceMode.any);
}

class PlaceAutocompleteField extends StatefulWidget {
  final TextEditingController controller;
  final String label;
  final String? hint;
  final int minChars;
  final void Function(PlaceSuggestion)? onSelected;
  final PlaceMode mode;
  final String? countryCode; // ISO 3166 alpha-2 — used in city mode
  final bool disabled;
  final String? disabledHint;

  const PlaceAutocompleteField({
    super.key,
    required this.controller,
    required this.label,
    this.hint,
    this.minChars = 2,
    this.onSelected,
    this.mode = PlaceMode.any,
    this.countryCode,
    this.disabled = false,
    this.disabledHint,
  });

  @override
  State<PlaceAutocompleteField> createState() => _PlaceAutocompleteFieldState();
}

class _PlaceAutocompleteFieldState extends State<PlaceAutocompleteField> {
  final _focusNode = FocusNode();
  final _layerLink = LayerLink();
  OverlayEntry? _overlay;
  Timer? _debounce;
  List<PlaceSuggestion> _suggestions = [];
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onChanged);
    _focusNode.addListener(_onFocusChange);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onChanged);
    _focusNode.removeListener(_onFocusChange);
    _focusNode.dispose();
    _debounce?.cancel();
    _removeOverlay();
    super.dispose();
  }

  void _onFocusChange() {
    if (!_focusNode.hasFocus) {
      Future.delayed(const Duration(milliseconds: 150), _removeOverlay);
    } else if (_suggestions.isNotEmpty) {
      _showOverlay();
    }
  }

  void _onChanged() {
    final q = widget.controller.text.trim();
    _debounce?.cancel();
    if (q.length < widget.minChars) {
      setState(() => _suggestions = []);
      _removeOverlay();
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 250), () => _fetch(q));
  }

  Future<void> _fetch(String q) async {
    setState(() => _loading = true);
    try {
      final count = widget.mode == PlaceMode.any ? 6 : 20;
      final params = <String, String>{
        'name': q,
        'count': '$count',
        'language': 'en',
        'format': 'json',
      };
      if (widget.mode == PlaceMode.city &&
          (widget.countryCode ?? '').isNotEmpty) {
        params['countryCode'] = widget.countryCode!;
      }
      final uri = Uri.parse(_geocodeBase).replace(queryParameters: params);
      final resp = await http.get(uri);
      if (resp.statusCode != 200) return;
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      final results = (data['results'] as List?) ?? const [];
      if (!mounted) return;
      final parsed = results
          .whereType<Map<String, dynamic>>()
          .map(PlaceSuggestion.fromJson)
          .toList();
      final filtered = _filterByMode(parsed);
      setState(() => _suggestions = filtered.take(6).toList());
      if (_suggestions.isNotEmpty && _focusNode.hasFocus) _showOverlay();
    } catch (_) {
      // network hiccup — silently drop suggestions
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<PlaceSuggestion> _filterByMode(List<PlaceSuggestion> list) {
    switch (widget.mode) {
      case PlaceMode.country:
        final seen = <String>{};
        return list.where((p) => (p.featureCode ?? '').startsWith('PCL')).where(
          (p) {
            final key = p.countryCode ?? p.country ?? p.name;
            if (seen.contains(key)) return false;
            seen.add(key);
            return true;
          },
        ).toList();
      case PlaceMode.city:
        return list
            .where((p) => (p.featureCode ?? '').startsWith('PPL'))
            .toList();
      case PlaceMode.any:
        return list;
    }
  }

  void _showOverlay() {
    _removeOverlay();
    final renderBox = context.findRenderObject() as RenderBox?;
    if (renderBox == null) return;
    final width = renderBox.size.width;
    _overlay = OverlayEntry(
      builder: (_) => Positioned(
        width: width,
        child: CompositedTransformFollower(
          link: _layerLink,
          showWhenUnlinked: false,
          targetAnchor: Alignment.bottomLeft,
          followerAnchor: Alignment.topLeft,
          offset: const Offset(0, -10),
          child: Material(
            color: Colors.transparent,
            child: Container(
              constraints: const BoxConstraints(maxHeight: 240),
              decoration: BoxDecoration(
                color: AppColors.surface1,
                border: Border.all(color: AppColors.border),
                borderRadius: BorderRadius.circular(10),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x99000000),
                    blurRadius: 24,
                    offset: Offset(0, 6),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: ListView.separated(
                  padding: EdgeInsets.zero,
                  shrinkWrap: true,
                  itemCount: _suggestions.length,
                  separatorBuilder: (_, _) => const Divider(
                    height: 1,
                    thickness: 1,
                    color: AppColors.border,
                  ),
                  itemBuilder: (_, i) {
                    final p = _suggestions[i];
                    final primary = widget.mode == PlaceMode.country
                        ? (p.country ?? p.name)
                        : p.name;
                    final secondary = widget.mode == PlaceMode.country
                        ? ''
                        : [
                            p.admin1,
                            p.country,
                          ].where((s) => (s ?? '').isNotEmpty).join(', ');
                    return InkWell(
                      onTap: () => _pick(p),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 11,
                        ),
                        child: Row(
                          children: [
                            const Opacity(
                              opacity: 0.6,
                              child: Text('📍', style: TextStyle(fontSize: 13)),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: RichText(
                                overflow: TextOverflow.ellipsis,
                                text: TextSpan(
                                  style: const TextStyle(
                                    color: AppColors.cream,
                                    fontSize: 14,
                                  ),
                                  children: [
                                    TextSpan(text: primary),
                                    if (secondary.isNotEmpty)
                                      TextSpan(
                                        text: '  $secondary',
                                        style: const TextStyle(
                                          color: AppColors.creamDim,
                                          fontSize: 12,
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          ),
        ),
      ),
    );
    Overlay.of(context).insert(_overlay!);
  }

  void _removeOverlay() {
    _overlay?.remove();
    _overlay = null;
  }

  void _pick(PlaceSuggestion p) {
    final lbl = p.labelFor(widget.mode);
    widget.controller.text = lbl;
    widget.controller.selection = TextSelection.collapsed(offset: lbl.length);
    widget.onSelected?.call(p);
    _focusNode.unfocus();
    _removeOverlay();
  }

  @override
  Widget build(BuildContext context) {
    return CompositedTransformTarget(
      link: _layerLink,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.label.toUpperCase(),
              style: const TextStyle(
                color: AppColors.creamDim,
                fontSize: 11,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 6),
            TextFormField(
              controller: widget.controller,
              focusNode: _focusNode,
              enabled: !widget.disabled,
              style: const TextStyle(color: AppColors.cream, fontSize: 15),
              decoration: InputDecoration(
                hintText:
                    widget.disabled && (widget.disabledHint ?? '').isNotEmpty
                    ? widget.disabledHint
                    : widget.hint,
                suffixIcon: _loading
                    ? const Padding(
                        padding: EdgeInsets.all(12),
                        child: SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: AppColors.terraLight,
                          ),
                        ),
                      )
                    : null,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
