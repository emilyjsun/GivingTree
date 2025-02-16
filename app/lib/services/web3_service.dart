import 'package:http/http.dart' as http;
import 'package:web3dart/web3dart.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:web_socket_channel/io.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'dart:convert';

class CharityInfo {
  final String name;
  final String address;
  final BigInt percentage;

  CharityInfo({
    required this.name,
    required this.address,
    required this.percentage,
  });
}

class UserTopicsData {
  final List<String> topics;
  final List<CharityInfo> charities;
  final BigInt balance;

  UserTopicsData({
    required this.topics,
    required this.charities,
    required this.balance,
  });
}

class Web3Service {
  static final Web3Service _instance = Web3Service._internal();
  static Web3Service get instance => _instance;

  late final Web3Client client;
  late final DeployedContract contract;

  // Sepolia testnet
  static const String rpcUrl = "https://sepolia.infura.io/v3/3ec58a866a9d418f8bd2857952d4fcf0";
  static const String wsUrl = "wss://sepolia.infura.io/ws/v3/3ec58a866a9d418f8bd2857952d4fcf0";
  static const String contractAddress = "0x01786AA502BEeF1862691399C5A526E4Ce16F43d";
  
  Web3Service._internal() {
    client = Web3Client(
      rpcUrl, 
      http.Client(),
      socketConnector: () {
        return IOWebSocketChannel.connect(wsUrl).cast<String>();
      },
    );
  }

  Future<void> initialize() async {
    final abiString = await rootBundle.loadString('assets/abi/contract.json');
    contract = DeployedContract(
      ContractAbi.fromJson(abiString, 'Owner'),
      EthereumAddress.fromHex(contractAddress),
    );

    // Set up event subscription
    final donatedEvent = contract.event('Donated');
    final subscription = client.events(FilterOptions.events(
      contract: contract,
      event: donatedEvent,
    )).listen((event) {
      final decoded = donatedEvent.decodeResults(event.topics!, event.data!);
      print('Donation from: ${decoded[0]} amount: ${decoded[1]}');
    });
  }

  Future<String> sendDonation(String fromAddress, BigInt weiAmount) async {
    final privateKey = dotenv.env['PRIVATE_KEY'];
    if (privateKey == null) throw Exception('Private key not found in environment');
    
    final credentials = EthPrivateKey.fromHex(privateKey);
    final donateFunction = contract.function('donate');

    final transaction = Transaction.callContract(
      contract: contract,
      function: donateFunction,
      parameters: [],
      from: credentials.address,
      value: EtherAmount.inWei(weiAmount),
    );

    final txHash = await client.sendTransaction(
      credentials,
      transaction,
      chainId: 11155111, // Sepolia chain ID
    );

    return txHash;
  }

  Future<BigInt> getBalance(String address) async {
    final balanceFunction = contract.function('balanceOf');
    final balance = await client.call(
      contract: contract,
      function: balanceFunction,
      params: [EthereumAddress.fromHex(address)],
    );
    return balance.first as BigInt;
  }

  Future<TransactionReceipt?> getTransactionReceipt(String txHash) async {
    return await client.getTransactionReceipt(txHash);
  }

  Future<List<DonationEvent>> getPastDonations(String address) async {
    try {
      final donatedEvent = contract.event('Donated');
      final currentBlock = await client.getBlockNumber();
      
      // Get private key address
      final privateKey = dotenv.env['PRIVATE_KEY'];
      if (privateKey == null) throw Exception('Private key not found in environment');
      final credentials = EthPrivateKey.fromHex(privateKey);
      final privateAddress = credentials.address.hex;
      
      print('Fetching donations for private address: $privateAddress');
      print('Current block: $currentBlock');
      
      final events = await client.getLogs(
        FilterOptions.events(
          contract: contract,
          event: donatedEvent,
          fromBlock: const BlockNum.exact(0),
          toBlock: BlockNum.exact(currentBlock),
        ),
      );

      print('Found ${events.length} total events');
      
      final donations = events.map((event) {
        final decoded = donatedEvent.decodeResults(event.topics!, event.data!);
        final donorAddress = (decoded[0] as EthereumAddress).hex;
        final amount = (decoded[1] as BigInt);
        print('Donation from: $donorAddress, amount: $amount');
        return DonationEvent(
          from: donorAddress,
          amount: amount,
          timestamp: DateTime.now(),
        );
      }).where((event) => 
        event.from.toLowerCase() == privateAddress.toLowerCase()
      ).toList()
        ..sort((a, b) => b.timestamp.compareTo(a.timestamp));

      print('Filtered to ${donations.length} donations for private address');
      return donations;
    } catch (e) {
      print('Error getting past donations: $e');
      return [];
    }
  }

  Future<List<BigInt>> getPortfolioDistribution(String address) async {
    // Commented out real implementation
    // try {
    //   final getUserTopicsFunction = contract.function('getUserTopics');
    //   final result = await client.call(
    //     contract: contract,
    //     function: getUserTopicsFunction,
    //     params: [EthereumAddress.fromHex(address)],
    //   );
      
    //   if (result.isEmpty) return [];
      
    //   final percentages = (result[2] as List).cast<BigInt>();
    //   return percentages;
    // } catch (e) {
    //   print('Error getting portfolio distribution: $e');
    //   return [];
    // }

    // Return fake data for 3 charities
    return [
      BigInt.from(50),  // 50% to first charity
      BigInt.from(30),  // 30% to second charity
      BigInt.from(20),  // 20% to third charity
    ];
  }

  Future<UserTopicsData> getUserTopics(String address) async {
    try {
      final getUserTopicsFunction = contract.function('getUserTopics');
      final result = await client.call(
        contract: contract,
        function: getUserTopicsFunction,
        params: [EthereumAddress.fromHex(address)],
      );
      
      final topics = (result[0] as List).cast<String>();
      final charityAddresses = (result[1] as List).cast<EthereumAddress>();
      final percentages = (result[2] as List).cast<BigInt>();
      final balance = result[3] as BigInt;

      // Get charity names from API
      final response = await http.post(
        Uri.parse('http://44.192.60.208:81/charityaddress'),
        body: jsonEncode({
          'addresses': charityAddresses.map((addr) => addr.hex).toList(),
        }),
        headers: {'Content-Type': 'application/json'},
      );

      final charityData = jsonDecode(response.body);
      
      final charities = List.generate(
        charityAddresses.length,
        (i) => CharityInfo(
          name: charityData[charityAddresses[i].hex] as String,  // Use address as key
          address: charityAddresses[i].hex,
          percentage: percentages[i],
        ),
      );

      return UserTopicsData(
        topics: topics,
        charities: charities,
        balance: balance,
      );
    } catch (e) {
      print('Error getting user topics: $e');
      // Return fake data for now
      return UserTopicsData(
        topics: [],  // Empty topics list
        charities: [
          CharityInfo(
            name: 'Green Earth',
            address: '0x...',
            percentage: BigInt.from(50),
          ),
          CharityInfo(
            name: 'Schools First',
            address: '0x...',
            percentage: BigInt.from(30),
          ),
          CharityInfo(
            name: 'Health For All',
            address: '0x...',
            percentage: BigInt.from(20),
          ),
        ],
        balance: BigInt.zero,
      );
    }
  }

  void dispose() {
    client.dispose();
  }
}

class DonationEvent {
  final String from;
  final BigInt amount;
  final DateTime timestamp;

  DonationEvent({
    required this.from,
    required this.amount,
    required this.timestamp,
  });
} 