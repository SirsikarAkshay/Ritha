import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../state/auth_provider.dart';
import '../theme/app_theme.dart';

class HomeShell extends StatelessWidget {
  final Widget child;
  const HomeShell({super.key, required this.child});

  static const _tabs = <_Tab>[
    _Tab('/',              Icons.dashboard_outlined,     'Home'),
    _Tab('/wardrobe',      Icons.checkroom_outlined,     'Wardrobe'),
    _Tab('/itinerary',     Icons.event_note_outlined,    'Schedule'),
    _Tab('/trips',         Icons.flight_takeoff_outlined,'Trips'),
    _Tab('/cultural',      Icons.public_outlined,        'Cultural'),
  ];

  int _indexOf(String location) {
    for (var i = 0; i < _tabs.length; i++) {
      final p = _tabs[i].path;
      if (location == p || (p != '/' && location.startsWith(p))) return i;
    }
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final currentIndex = _indexOf(location);
    final auth = context.watch<AuthProvider>();
    return Scaffold(
      backgroundColor: AppColors.midnight,
      appBar: AppBar(
        backgroundColor: AppColors.midnight,
        elevation: 0,
        title: const Text('Ritha', style: TextStyle(color: AppColors.cream, fontWeight: FontWeight.w700)),
        actions: [
          IconButton(
            icon: const Icon(Icons.person_outline, color: AppColors.cream),
            tooltip: 'Profile',
            onPressed: () => context.go('/profile'),
          ),
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert, color: AppColors.cream),
            color: AppColors.surface1,
            onSelected: (v) {
              switch (v) {
                case 'sustainability':  context.go('/sustainability'); break;
                case 'people':          context.go('/people'); break;
                case 'messages':        context.go('/messages'); break;
                case 'shared':          context.go('/shared-wardrobes'); break;
                case 'logout':          auth.logout(); break;
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'sustainability', child: Text('Sustainability',     style: TextStyle(color: AppColors.cream))),
              PopupMenuItem(value: 'people',         child: Text('People',             style: TextStyle(color: AppColors.cream))),
              PopupMenuItem(value: 'messages',       child: Text('Messages',           style: TextStyle(color: AppColors.cream))),
              PopupMenuItem(value: 'shared',         child: Text('Shared wardrobes',   style: TextStyle(color: AppColors.cream))),
              PopupMenuDivider(),
              PopupMenuItem(value: 'logout',         child: Text('Sign out',           style: TextStyle(color: AppColors.danger))),
            ],
          ),
        ],
      ),
      body: child,
      bottomNavigationBar: NavigationBar(
        backgroundColor: AppColors.surface1,
        indicatorColor: AppColors.terraDim,
        selectedIndex: currentIndex,
        onDestinationSelected: (i) => context.go(_tabs[i].path),
        destinations: [
          for (final t in _tabs)
            NavigationDestination(icon: Icon(t.icon, color: AppColors.creamDim), selectedIcon: Icon(t.icon, color: AppColors.terraLight), label: t.label),
        ],
      ),
    );
  }
}

class _Tab {
  final String path;
  final IconData icon;
  final String label;
  const _Tab(this.path, this.icon, this.label);
}
