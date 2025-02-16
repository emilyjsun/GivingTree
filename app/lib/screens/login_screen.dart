import 'package:flutter/material.dart';
import 'package:reown_appkit/reown_appkit.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../widgets/settings_content.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  late ReownAppKitModal _appKitModal;
  bool _isInitialized = false;
  late PageController _pageController;
  int _currentPage = 0;  // Add current page tracker

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
    _pageController.addListener(_onPageChange);  // Add page change listener
    _initializeAppKit();
  }

  @override
  void dispose() {
    _pageController.removeListener(_onPageChange);  // Remove listener
    _pageController.dispose();
    super.dispose();
  }

  void _onPageChange() {
    final page = _pageController.page?.round() ?? 0;
    if (page != _currentPage) {
      setState(() => _currentPage = page);
    }
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
      requiredNamespaces: const {
        'eip155': RequiredNamespace(
          chains: ['eip155:1'], // Ethereum mainnet
          methods: ['eth_sendTransaction', 'personal_sign'],
          events: ['chainChanged', 'accountsChanged'],
        ),
      },
    );

    // Update connection event to use page controller
    _appKitModal.onModalConnect.subscribe((ModalConnect? event) {
      if (mounted) {
        Navigator.of(context).pop();  // Close bottom sheet
        _pageController.animateToPage(
          2,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeInOut,
        );
      }
    });

    await _appKitModal.init();
    setState(() => _isInitialized = true);
  }

  void _onSoundsGoodPressed() {
    _pageController.animateToPage(
      1,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
    );
  }

  void _onGetStartedPressed() {
    Navigator.pushReplacementNamed(context, '/home');
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        image: DecorationImage(
          image: AssetImage('assets/images/green_header_bg.png'),
          fit: BoxFit.cover,
          alignment: Alignment.topCenter,
        ),
      ),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: PageView(
              controller: _pageController,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                _buildIntroTab(),
                _buildWalletConnectionTab(),
                _buildGetStartedTab(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDots() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(3, (index) => 
        Container(
          width: 8,
          height: 8,
          margin: const EdgeInsets.symmetric(horizontal: 4),
          decoration: BoxDecoration(
            color: _currentPage == index 
              ? const Color(0xFF119068)  // Update selected dot color
              : const Color(0xFFB2FFDD),  // Unselected light green
            shape: BoxShape.circle,
          ),
        ),
      ),
    );
  }

  Widget _buildIntroTab() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(),
          Image.asset(
            'assets/images/tree.png',
            height: 200,
          ),
          const SizedBox(height: 24),
          _buildDots(),
          const SizedBox(height: 64),
          const Text(
            'Welcome to\nThe Giving Tree!',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 32,
              fontWeight: FontWeight.bold,
              color: Color(0xFF119068),  // Update title color
              height: 1.2,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Use crypto to donate to\ncauses you are passionate about!',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Colors.white,
              height: 1.5,
            ),
          ),
          const Spacer(),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _onSoundsGoodPressed,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF27BF9D),
                padding: const EdgeInsets.symmetric(vertical: 8),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: const Text(
                'Sounds good!',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWalletConnectionTab() {
    if (!_isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(),
          Image.asset(
            'assets/images/flower_heart.png',
            height: 200,
          ),
          const SizedBox(height: 24),
          _buildDots(),
          const SizedBox(height: 64),
          const Text(
            'Connect your wallet to start\nmaking a difference',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Colors.white,
              height: 1.5,
            ),
          ),
          const Spacer(),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () {
                showModalBottomSheet(
                  context: context,
                  backgroundColor: Colors.transparent,
                  isScrollControlled: true,
                  constraints: BoxConstraints(
                    maxWidth: MediaQuery.of(context).size.width,
                    maxHeight: MediaQuery.of(context).size.height * 0.85, // Limit max height
                  ),
                  builder: (context) => Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(24),
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.vertical(
                        top: Radius.circular(24),
                      ),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'We currently only support transactions on ETH. More chains coming soon!',
                          style: TextStyle(
                            fontSize: 14,
                            color: Color(0xFF6B7280),
                            height: 1.5,
                          ),
                        ),
                        const SizedBox(height: 16),
                        const Divider(height: 1, color: Color(0xFFE5E7EB)),
                        const SizedBox(height: 16),
                        Center(
                          child: Column(
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
                        ),
                      ],
                    ),
                  ),
                );
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF27BF9D),
                padding: const EdgeInsets.symmetric(vertical: 8),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: const Text(
                'Connect Wallet',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGetStartedTab() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(),
          Image.asset(
            'assets/images/leaf-flow.png',
            height: 200,
          ),
          const SizedBox(height: 24),
          _buildDots(),
          const SizedBox(height: 64),
          const Text(
            'Set up custom preferences\nfor portfolio optimization',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Colors.white,
              height: 1.5,
            ),
          ),
          const Spacer(),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () {
                showModalBottomSheet(
                  context: context,
                  backgroundColor: Colors.transparent,
                  isScrollControlled: true,
                  constraints: BoxConstraints(
                    maxWidth: MediaQuery.of(context).size.width,
                    maxHeight: MediaQuery.of(context).size.height * 0.85, // Limit max height
                  ),
                  builder: (context) => Padding(
                    padding: EdgeInsets.only(
                      bottom: MediaQuery.of(context).viewInsets.bottom,
                    ),
                    child: SingleChildScrollView(
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(24),
                        decoration: const BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.vertical(
                            top: Radius.circular(24),
                          ),
                        ),
                        child: SettingsContent(
                          showSaveButton: true,
                          onComplete: _onGetStartedPressed,
                        ),
                      ),
                    ),
                  ),
                );
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF27BF9D),
                padding: const EdgeInsets.symmetric(vertical: 8),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: const Text(
                'Set Preferences',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}  