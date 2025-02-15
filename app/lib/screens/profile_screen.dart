import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

class ProfileTab extends StatefulWidget {
  const ProfileTab({super.key});

  @override
  State<ProfileTab> createState() => _ProfileTabState();
}

class _ProfileTabState extends State<ProfileTab> {
  int _currentChartIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        image: DecorationImage(
          image: AssetImage('assets/images/blue_header_bg.png'),
          fit: BoxFit.cover,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 60),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 20),
            child: Text(
              'Financial Overview',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
          ),
          const SizedBox(height: 20),
          GestureDetector(
            onHorizontalDragEnd: (details) {
              setState(() {
                if (details.primaryVelocity! < 0) {
                  // Swipe left
                  _currentChartIndex = 1;
                } else {
                  // Swipe right
                  _currentChartIndex = 0;
                }
              });
            },
            child: SizedBox(
              height: 200,
              child: _buildPieChart(),
            ),
          ),
          Expanded(
            child: Container(
              margin: const EdgeInsets.only(top: 20),
              padding: const EdgeInsets.all(20),
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
              ),
              child: const RecentTransactionsWidget(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPieChart() {
    return PieChart(
      PieChartData(
        sections: _currentChartIndex == 0 ? _buildExpenseSections() : _buildIncomeSections(),
        sectionsSpace: 2,
        centerSpaceRadius: 40,
        startDegreeOffset: 270,
      ),
    );
  }

  List<PieChartSectionData> _buildExpenseSections() {
    return [
      PieChartSectionData(
        value: 35,
        title: 'Housing',
        color: Colors.blue,
        radius: 60,
      ),
      PieChartSectionData(
        value: 25,
        title: 'Food',
        color: Colors.green,
        radius: 60,
      ),
      PieChartSectionData(
        value: 20,
        title: 'Transport',
        color: Colors.orange,
        radius: 60,
      ),
      PieChartSectionData(
        value: 20,
        title: 'Other',
        color: Colors.red,
        radius: 60,
      ),
    ];
  }

  List<PieChartSectionData> _buildIncomeSections() {
    return [
      PieChartSectionData(
        value: 60,
        title: 'Salary',
        color: Colors.green,
        radius: 60,
      ),
      PieChartSectionData(
        value: 30,
        title: 'Investments',
        color: Colors.blue,
        radius: 60,
      ),
      PieChartSectionData(
        value: 10,
        title: 'Other',
        color: Colors.orange,
        radius: 60,
      ),
    ];
  }
}

class RecentTransactionsWidget extends StatelessWidget {
  const RecentTransactionsWidget({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Recent Transactions',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 15),
        Expanded(
          child: ListView.builder(
            itemCount: 10,
            itemBuilder: (context, index) {
              return ListTile(
                leading: const CircleAvatar(
                  backgroundColor: Colors.grey,
                  child: Icon(Icons.shopping_bag, color: Colors.white),
                ),
                title: Text('Transaction ${index + 1}'),
                subtitle: Text('March ${index + 1}, 2024'),
                trailing: Text('\$${(index + 1) * 10}.00'),
              );
            },
          ),
        ),
      ],
    );
  }
} 