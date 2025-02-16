import 'package:flutter/material.dart';
import 'overview_screen.dart';
import 'profile_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        extendBody: true,
        body: const TabBarView(
          children: [
            OverviewTab(),
            ProfileTab(),
            SettingsTab(),
          ],
        ),
        bottomNavigationBar: Container(
          margin: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(50),
            color: Colors.white,
            border: Border.all(
              color: const Color(0xFFB6B8BE),
              width: 1,
            ),
          ),
          child: TabBar(
            tabs: const [
              Tab(icon: Icon(Icons.dashboard_outlined)),
              Tab(icon: Icon(Icons.person_outline)),
              Tab(icon: Icon(Icons.settings_outlined)),
            ],
            indicator: const BoxDecoration(),
            labelColor: const Color(0xFF27BF9D),
            unselectedLabelColor: const Color(0xFFB6B8BE),
            padding: const EdgeInsets.symmetric(vertical: 16),
            dividerColor: Colors.transparent,
          ),
        ),
      ),
    );
  }
} 