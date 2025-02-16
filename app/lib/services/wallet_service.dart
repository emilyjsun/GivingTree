import 'package:flutter/material.dart';
import 'package:reown_appkit/reown_appkit.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class WalletService {
  static WalletService? _instance;
  ReownAppKitModal? _appKit;
  bool _isInitialized = false;

  // Private constructor
  WalletService._();

  // Singleton instance getter
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
    // Always dispose existing instance before creating a new one
    await dispose();

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
      await _appKit!.disconnect();
      await dispose();
    }
  }
} 