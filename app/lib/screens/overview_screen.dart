import 'package:flutter/material.dart';
import 'package:reown_appkit/modal/models/public/appkit_modal_session.dart';
import '../widgets/growing_tree.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:web3dart/web3dart.dart';
import '../services/wallet_service.dart';
import '../services/web3_service.dart';
import '../widgets/toast_notification.dart';
import '../services/toast_service.dart';

class OverviewTab extends StatefulWidget {
  const OverviewTab({super.key});

  @override
  State<OverviewTab> createState() => _OverviewTabState();
}

class _OverviewTabState extends State<OverviewTab> {
  final _treeKey = GlobalKey<GrowingTreeState>();
  bool _isMaxDepthReached = false;
  final TextEditingController _amountController = TextEditingController();

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  void _showToast(ToastNotification toast) {
    final overlay = Overlay.of(context);
    late OverlayEntry overlayEntry;
    
    overlayEntry = OverlayEntry(
      builder: (context) => toast,
    );

    overlay.insert(overlayEntry);
    
    Future.delayed(const Duration(seconds: 2), () async {
      final toastState = toast.toastKey.currentState;
      if (toastState != null) {
        try {
          await toastState.dismiss();
          if (mounted) {  // Check if widget is still mounted
            overlayEntry.remove();
          }
        } catch (e) {
          print('Toast dismiss error: $e');
        }
      } else {
        overlayEntry.remove();
      }
    });
  }

  Future<void> _showDonationModal() async {
    final appKit = WalletService.instance.appKit;
    final web3 = Web3Service.instance;
    String? balance;

    if (appKit.session != null) {
      final address = appKit.session!.getAddress('eip155');
      if (address != null) {
        final ethBalance = await web3.client.getBalance(EthereumAddress.fromHex(address));
        balance = '${ethBalance.getValueInUnit(EtherUnit.ether).toStringAsFixed(4)} ETH';
      }
    }

    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(
              top: Radius.circular(24),
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Add Funds',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              if (balance != null) ...[
                const SizedBox(height: 8),
                Text(
                  'Current Balance: $balance',
                  style: const TextStyle(
                    fontSize: 16,
                    color: Color(0xFF666666),
                  ),
                ),
              ],
              const SizedBox(height: 16),
              TextField(
                controller: _amountController,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  labelText: 'Amount (ETH)',
                  border: OutlineInputBorder(),
                  hintText: '0.01',
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () {
                    final amount = double.tryParse(_amountController.text);
                    if (amount != null && amount > 0) {
                      Navigator.pop(context);
                      donateContract(amount);
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF27BF9D),
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Text(
                    'Confirm Donation',
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
        ),
      ),
    );
  }

  Future<void> donateContract(double amount) async {
    try {
      // Show pending notification
      ToastService.instance.showToast(
        message: 'Transaction Submitted',
        backgroundColor: Colors.grey,
        icon: const Icon(Icons.info_outline, color: Colors.white, size: 16),
      );

      final appKit = WalletService.instance.appKit;
      final web3 = Web3Service.instance;
      if (appKit.session != null) {
        final address = appKit.session!.getAddress('eip155');
        if (address == null) {
          debugPrint('Error: No wallet address found');
          return;
        }

        final weiAmount = BigInt.from(amount * 1e18);
        
        print("Sending donation transaction");
        
        final txHash = await web3.sendDonation(address, weiAmount);
        print('Transaction hash: $txHash');
        
        // Wait for transaction confirmation
        bool confirmed = false;
        while (!confirmed) {
          final receipt = await web3.getTransactionReceipt(txHash);
          if (receipt != null) {
            confirmed = true;
            if (receipt.status!) {
              print('Donation confirmed!');
              // Show success notification
              ToastService.instance.showToast(
                message: 'Donation successful!',
                backgroundColor: const Color(0xFF27BF9D),
                icon: const Icon(Icons.check_circle, color: Colors.white, size: 16),
              );
              
              final state = _treeKey.currentState;
              if (!_isMaxDepthReached) {
                state?.addBranch();
              }
            } else {
              print('Donation failed');
              // Show error notification
              ToastService.instance.showToast(
                message: 'Transaction failed',
                backgroundColor: Colors.red,
                icon: const Icon(Icons.error, color: Colors.white, size: 16),
              );
            }
          } else {
            await Future.delayed(const Duration(seconds: 1));
          }
        }
      }
    } catch (e) {
      print('Error during donation: $e');
      // Show simplified error notification
      ToastService.instance.showToast(
        message: 'An error occurred',
        backgroundColor: Colors.red,
        icon: const Icon(Icons.error, color: Colors.white, size: 16),
      );
    }
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
        extendBody: true,
        backgroundColor: Colors.transparent,
        body: Stack(
          children: [
            Center(
              child: GrowingTree(
                key: _treeKey,
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: Image.asset(
                'assets/images/ground_fg.png',
                fit: BoxFit.fitWidth,
              ),
            ),
            Positioned(
              bottom: 132,
              left: 32,
              right: 32,
              child: Center(
                child: SizedBox(
                  height: 56,
                  child: ElevatedButton(
                    onPressed: _showDonationModal,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF27BF9D),
                      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(30),
                      ),
                    ),
                    child: Text(
                      'Add Funds',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
} 