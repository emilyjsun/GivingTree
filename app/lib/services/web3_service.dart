import 'package:http/http.dart';
import 'package:web3dart/web3dart.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:web_socket_channel/io.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

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
      Client(),
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
    final donatedEvent = contract.event('Donated');
    final currentBlock = await client.getBlockNumber();
    
    final events = await client.getLogs(
      FilterOptions.events(
        contract: contract,
        event: donatedEvent,
        fromBlock: const BlockNum.exact(0), // Start from beginning
        toBlock: BlockNum.exact(currentBlock),
      ),
    );

    return events.map((event) {
      final decoded = donatedEvent.decodeResults(event.topics!, event.data!);
      return DonationEvent(
        from: (decoded[0] as EthereumAddress).hex,
        amount: (decoded[1] as BigInt),
        timestamp: DateTime.now(), // Ideally get this from block timestamp
      );
    }).where((event) => 
      event.from.toLowerCase() == address.toLowerCase()
    ).toList()
      ..sort((a, b) => b.timestamp.compareTo(a.timestamp));
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