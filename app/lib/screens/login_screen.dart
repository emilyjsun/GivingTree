import 'package:flutter/material.dart';
import 'package:reown_appkit/reown_appkit.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  late ReownAppKitModal _appKitModal;
  bool _isInitialized = false;

  @override
  void initState() {
    super.initState();
    _initializeAppKit();
  }

  Future<void> _initializeAppKit() async {
    final projectId = dotenv.env['REOWN_PROJECT_ID'];

    // AppKit Modal instance
    _appKitModal = ReownAppKitModal(
      context: context,
      projectId: projectId,
      metadata: const PairingMetadata(
        name: 'The Giving Tree',
        description: 'An efficient, intelligent donation management engine.',
        url: '',
        icons: [''],
        redirect: Redirect(
          native: 'givingtree://',
          linkMode: false,
        ),
      ),
    );

    // Register here the event callbacks on the service you'd like to use. See `Events` section.

    await _appKitModal.init();
    setState(() => _isInitialized = true);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        image: DecorationImage(
          image: AssetImage('assets/images/sky_bg.png'),
          fit: BoxFit.cover,
          alignment: Alignment.topCenter,
        ),
      ),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const Spacer(),
                const Text(
                  'Welcome to\nThe Giving Tree',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1F2937),
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'Connect your wallet to get started',
                  style: TextStyle(
                    fontSize: 16,
                    color: Color(0xFF6B7280),
                  ),
                ),
                const Spacer(),
                if (_isInitialized)
                  Padding(
                    padding: const EdgeInsets.all(32.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        AppKitModalNetworkSelectButton(appKit: _appKitModal),
                        const SizedBox(height: 16),
                        AppKitModalConnectButton(appKit: _appKitModal),
                        Visibility(
                          visible: _appKitModal.isConnected,
                          child: AppKitModalAccountButton(appKitModal: _appKitModal),
                        ),
                      ],
                    ),
                  )
                else
                  const Center(child: CircularProgressIndicator()),
              ],
            ),
          ),
        ),
      ),
    );
  }
} 