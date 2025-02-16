import 'package:flutter/material.dart';
import 'package:reown_appkit/reown_appkit.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class WalletService {
  static WalletService? _instance;
  ReownAppKitModal? _appKit;
  bool _isInitialized = false;

  WalletService._();

  static WalletService get instance {
    _instance ??= WalletService._();
    return _instance!;
  }

  ReownAppKitModal get appKit {
    if (!_isInitialized || _appKit == null) {
      throw Exception('WalletService not initialized. Call init() first.');
    }
    return _appKit!;
  }

  Future<void> init(BuildContext context) async {
    if (_isInitialized && _appKit != null) return;

    final projectId = dotenv.env['REOWN_PROJECT_ID'];
    _appKit = ReownAppKitModal(
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
      requiredNamespaces: const {
        'eip155': RequiredNamespace(
          chains: ['eip155:11155111'], // Ethereum mainnet
          methods: ['eth_sendTransaction', 'personal_sign'],
          events: ['chainChanged', 'accountsChanged'],
        ),
      },
    );

    await _appKit?.init();
    _isInitialized = true;
  }

  Future<void> dispose() async {
    if (_isInitialized && _appKit != null) {
      await _appKit!.dispose();
      _appKit = null;
      _isInitialized = false;
    }
  }

  bool get isConnected => _isInitialized && _appKit?.isConnected == true;

  Future<void> disconnect() async {
    if (_isInitialized && _appKit != null) {
      if (_appKit!.isConnected) {
        await _appKit!.disconnect();
        await dispose(); // dispose to clear the appkit instance
      }
    }
  }

  String? getAddress() {
    try {
      const namespace = 'eip155';
      return _appKit?.session?.getAddress(namespace);
    } catch (e) {
      return null;
    }
  }
} 