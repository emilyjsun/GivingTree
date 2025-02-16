import 'package:flutter/material.dart';
import 'overview_screen.dart';
import 'profile_screen.dart';
import 'settings_screen.dart';
import '../widgets/toast_notification.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  HomeScreenState createState() => HomeScreenState();
}

class HomeScreenState extends State<HomeScreen> {
  OverlayEntry? _currentToast;

  @override
  void dispose() {
    _currentToast?.remove();
    super.dispose();
  }

  void showToast({
    required String message,
    Color backgroundColor = Colors.grey,
    Widget? icon,
  }) {
    _currentToast?.remove();
    
    final overlay = Overlay.of(context);
    _currentToast = OverlayEntry(
      builder: (context) => ToastNotification(
        message: message,
        backgroundColor: backgroundColor,
        icon: icon,
      ),
    );

    overlay.insert(_currentToast!);

    Future.delayed(const Duration(seconds: 2), () {
      _currentToast?.remove();
      _currentToast = null;
    });
  }

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