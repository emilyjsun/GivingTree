import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'transaction_screen.dart';

class ProfileTab extends StatefulWidget {
  const ProfileTab({super.key});

  @override
  State<ProfileTab> createState() => _ProfileTabState();
}

// final address = WalletService.instance.getAddress(); to get address
class _ProfileTabState extends State<ProfileTab> {
  int _currentPage = 0;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        image: DecorationImage(
          image: AssetImage('assets/images/blue_header_bg.png'),
          fit: BoxFit.cover,
          alignment: Alignment.topCenter,
        ),
      ),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          title: Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const Text(
                  'My Portfolio',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                const Text(
                  'Donation Breakdown',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF88BAC5),
                  ),
                ),
              ],
            ),
          ),
          centerTitle: true,
        ),
        body: Stack(
          children: [
            // White background container
            Container(
              margin: const EdgeInsets.only(top: 120),
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(
                  top: Radius.circular(30),
                ),
              ),
            ),
            // Content
            Column(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  height: 250,
                  child: PageView(
                    onPageChanged: (index) {
                      setState(() {
                        _currentPage = index;
                      });
                    },
                    children: [
                      _buildPieChart(),
                      _buildSecondPieChart(),
                    ],
                  ),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: _currentPage == 0 
                            ? const Color(0xFF27BF9D)
                            : Colors.grey.shade300,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: _currentPage == 1 
                            ? const Color(0xFF27BF9D)
                            : Colors.grey.shade300,
                      ),
                    ),
                  ],
                ),
                Expanded(
                  child: SafeArea(
                    child: Container(
                      padding: const EdgeInsets.all(16),
                      child: const RecentTransactionsWidget(),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPieChart() {
    return PieChart(
      PieChartData(
        sections: [
          PieChartSectionData(
            value: 35,
            color: const Color(0xFF27BF9D),
            showTitle: false,
          ),
          PieChartSectionData(
            value: 25,
            color: const Color(0xFF13A47D),
            showTitle: false,
          ),
          PieChartSectionData(
            value: 20,
            color: const Color(0xFF119068),
            showTitle: false,
          ),
          PieChartSectionData(
            value: 20,
            color: const Color(0xFFCAEEDE),
            showTitle: false,
          ),
        ],
        sectionsSpace: 0,
        centerSpaceRadius: 65,
        centerSpaceColor: Colors.white,
        startDegreeOffset: 270,
      ),
    );
  }

  Widget _buildSecondPieChart() {
    return PieChart(
      PieChartData(
        sections: [
          PieChartSectionData(
            value: 100,
            showTitle: false,
            gradient: const SweepGradient(
              colors: [
                Color(0xFFC6EDDB),
                Color(0xFF27BF9D),
                Color(0xFFC6EDDB),
              ],
            ),
          ),
        ],
        sectionsSpace: 0,
        centerSpaceRadius: 65,
        centerSpaceColor: Colors.white,
        startDegreeOffset: 270,
      ),
    );
  }
}

class RecentTransactionsWidget extends StatelessWidget {
  const RecentTransactionsWidget({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(
          color: Colors.grey.shade300,
          width: 1,
        ),
        borderRadius: BorderRadius.circular(30),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Recent Transactions',
                style: TextStyle(
                  fontSize: 16,
                ),
              ),
              Container(
                decoration: BoxDecoration(
                  border: Border.all(
                    color: Colors.grey.shade300,
                    width: 1,
                  ),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: TextButton(
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const TransactionScreen(),
                      ),
                    );
                  },
                  child: const Text(
                    'View All',
                    style: TextStyle(
                      color: Colors.black,
                      fontSize: 16,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Divider(
            color: Colors.grey.shade300,
            height: 1,
          ),
          Expanded(
            child: ListView.builder(
              padding: EdgeInsets.zero,
              itemCount: 10,
              itemBuilder: (context, index) {
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: const Color(0xFFA1E1C4),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      Icons.shopping_bag,
                      color: Colors.white,
                      size: 20,
                    ),
                  ),
                  title: Text(
                    'Transaction ${index + 1}',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  subtitle: Text('March ${index + 1}, 2024'),
                  trailing: Text(
                    '\$${(index + 1) * 10}.00',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
} 