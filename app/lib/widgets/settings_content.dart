import 'package:flutter/material.dart';
import 'settings_toggle.dart';
import '../services/wallet_service.dart';

class SettingsContent extends StatefulWidget {
  final VoidCallback? onComplete;
  final bool showSaveButton;

  const SettingsContent({
    super.key,
    this.onComplete,
    this.showSaveButton = true,
  });

  @override
  State<SettingsContent> createState() => _SettingsContentState();
}

class _SettingsContentState extends State<SettingsContent> {
  bool _prioritizeCurrentEvents = false;
  bool _enablePushNotifications = false;
  final TextEditingController _missionController = TextEditingController();

  @override
  void dispose() {
    _missionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 24, vertical: 24),
          child: Text(
            'These settings control the behavior of your portfolio optimization agent.',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: Color(0xFF6B7280),
            ),
          ),
        ),
        Divider(
          color: Colors.grey.shade300,
          thickness: 1,
        ),
        SettingsToggle(
          title: 'Prioritize current events',
          value: _prioritizeCurrentEvents,
          onChanged: (value) {
            setState(() {
              _prioritizeCurrentEvents = value;
            });
          },
        ),
        SettingsToggle(
          title: 'Enable push notifications',
          value: _enablePushNotifications,
          onChanged: (value) {
            setState(() {
              _enablePushNotifications = value;
            });
          },
        ),
        const SizedBox(height: 16),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 24),
          child: Text(
            'My Mission Statement',
            style: TextStyle(
              fontSize: 16,
              color: Color(0xFF1F2937),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: TextField(
            controller: _missionController,
            maxLines: 5,
            style: const TextStyle(
              color: Color(0xFF6B7280),
            ),
            decoration: InputDecoration(
              contentPadding: const EdgeInsets.all(16),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(
                  color: Colors.grey.shade300,
                  width: 1,
                ),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(
                  color: Colors.grey.shade300,
                  width: 1,
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(
                  color: Colors.grey.shade300,
                  width: 1,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 24),
        if (widget.showSaveButton)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: widget.onComplete ?? () {
                  // Handle save
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF27BF9D),
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                child: Text(
                  widget.onComplete != null ? 'Get Started' : 'Save Mission Statement',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ),
        const SizedBox(height: 16),
        if (widget.showSaveButton)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () async {
                  final confirmed = await showDialog<bool>(
                    context: context,
                    builder: (BuildContext context) {
                      return AlertDialog(
                        backgroundColor: Colors.white,
                        content: const Text(
                          'Are you sure you want to disconnect your wallet?',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Color(0xFF6B7280),
                          ),
                        ),
                        actions: <Widget>[
                          SizedBox(
                            width: 120,
                            child: ElevatedButton(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Color(0xFF27BF9D),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(16),
                                ),
                              ),
                              onPressed: () => Navigator.of(context).pop(true),
                              child: const Text(
                                'Confirm',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ),
                          SizedBox(
                            width: 120,
                            child: TextButton(
                              onPressed: () => Navigator.of(context).pop(false),
                              child: const Text(
                                'Cancel',
                                style: TextStyle(
                                  color: Colors.grey,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ),
                        ],
                        actionsAlignment: MainAxisAlignment.spaceEvenly,
                      );
                    },
                  );

                  if (confirmed == true && context.mounted) {
                    await WalletService.instance.disconnect();
                    if (context.mounted) {
                      Navigator.pushReplacementNamed(context, '/login');
                    }
                  }
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.grey,
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                child: const Text(
                  'Log Out',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
} 