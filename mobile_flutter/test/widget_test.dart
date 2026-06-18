// Minimal smoke test. The full app (RithaApp) wires Firebase, secure storage,
// and routing, which aren't available in a plain widget test, so we verify the
// app theme builds and renders a basic frame instead.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ritha_mobile/theme/app_theme.dart';

void main() {
  testWidgets('app theme builds and renders a basic frame', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildAppTheme(),
        home: const Scaffold(body: Center(child: Text('Ritha'))),
      ),
    );

    expect(find.text('Ritha'), findsOneWidget);
  });
}
