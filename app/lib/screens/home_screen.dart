import 'package:flutter/material.dart';
import 'overview_screen.dart';
import 'profile_screen.dart';
import 'settings_screen.dart';
import '../services/wallet_service.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  Future<void> _showLogoutDialog(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Logout'),
          content: const Text('Are you sure you want to disconnect your wallet?'),
          actions: <Widget>[
            TextButton(
              child: const Text('Cancel'),
              onPressed: () => Navigator.of(context).pop(false),
            ),
            TextButton(
              child: const Text('Logout'),
              onPressed: () => Navigator.of(context).pop(true),
            ),
          ],
        );
      },
    );

    if (confirmed == true && context.mounted) {
      await WalletService.instance.disconnect();
      if (context.mounted) {
        Navigator.pushReplacementNamed(context, '/login');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      child: Scaffold(
        extendBody: true,
        body: const TabBarView(
          children: [
            OverviewTab(),
            ProfileTab(),
            SettingsTab(),
            SizedBox(),
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
              Tab(icon: Icon(Icons.logout_outlined)),
            ],
            indicator: const BoxDecoration(),
            labelColor: const Color(0xFF27BF9D),
            unselectedLabelColor: const Color(0xFFB6B8BE),
            padding: const EdgeInsets.symmetric(vertical: 16),
            dividerColor: Colors.transparent,
            onTap: (index) {
              if (index == 3) {
                _showLogoutDialog(context);
              }
            },
          ),
        ),
      ),
    );
  }
} 