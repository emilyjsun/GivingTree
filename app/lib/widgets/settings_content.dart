import 'package:flutter/material.dart';
import 'settings_toggle.dart';
import '../services/wallet_service.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class SettingsContent extends StatefulWidget {
  final Function onComplete;
  final String walletAddress;

  const SettingsContent({
    required this.onComplete,
    required this.walletAddress,
    Key? key
  }) : super(key: key);

  @override
  _SettingsContentState createState() => _SettingsContentState();
}

class _SettingsContentState extends State<SettingsContent> {
  bool _prioritizeCurrentEvents = false;
  bool _enablePushNotifications = false;
  final TextEditingController _missionController = TextEditingController();
  bool _instantUpdates = false;
  bool _isLoading = false;

  @override
  void dispose() {
    _missionController.dispose();
    super.dispose();
  }

  Future<void> _submitPreferences() async {
    if (_missionController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a mission statement')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final response = await http.post(
        Uri.parse('${dotenv.env['API_URL']}/userpreferences/create'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'userId': widget.walletAddress,
          'missionStatement': _missionController.text,
          'pushNotifs': _enablePushNotifications,
          'prioritizeCurrentEvents': _prioritizeCurrentEvents,
        }),
      );

      if (response.statusCode == 200) {
        final result = json.decode(response.body);
        
        // Show success message with categories
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Preferences saved!'),
                SizedBox(height: 4),
                Text(
                  'Categories: ${(result['data']['categories'] as List).map((c) => c[0]).join(", ")}',
                  style: TextStyle(fontSize: 12),
                ),
                SizedBox(height: 4),
                Text(
                  'Transaction: ${result['data']['contract_tx']}',
                  style: TextStyle(fontSize: 12),
                ),
              ],
            ),
            duration: Duration(seconds: 4),
          ),
        );
        
        widget.onComplete();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${response.body}')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Network error: $e')),
      );
    } finally {
      setState(() => _isLoading = false);
    }
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
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _submitPreferences,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF27BF9D),
                padding: const EdgeInsets.symmetric(vertical: 8),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: Text(
                _isLoading ? 'Saving...' : 'Save Preferences',
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
        if (widget.onComplete == null)
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
                    try {
                      // First navigate away from the current screen
                      Navigator.pushReplacementNamed(context, '/login');
                      // Then disconnect the wallet
                      await WalletService.instance.disconnect();
                    } catch (e) {
                      debugPrint('Error during logout: $e');
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