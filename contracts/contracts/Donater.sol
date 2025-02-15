// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/access/Ownable.sol";
import "hardhat/console.sol";

contract Donater is Ownable {

    constructor() Ownable(msg.sender) {}

    struct UserTopics {
        string[] ttopics;
        address[] charities;
        uint256[] charityPercents;
        uint256 balance;
    }

    modifier onlyUserOrOwner(address user) {
        require(msg.sender == user || msg.sender == owner(), "Not authorized");
        _;
    }

    mapping(address => UserTopics) public topics;

    event Donated(address indexed _user, uint256 _amount);
    event SplitAmongCharities(address indexed _user, uint256 _amount);

    function enroll(string[] memory _topics, address[] memory _charities, uint256[] memory _charityPercents) public {
        require(_topics.length == 3, "Topics must be 3");
        
        // console.log("Enrolling user: %s", msg.sender);
        // console.log("Topics: %s, %s, %s", _topics[0], _topics[1], _topics[2]);
        // console.log("Charity address: %s", _charity);
        
        topics[msg.sender] = UserTopics({
            ttopics: _topics,
            charities: _charities,
            charityPercents: _charityPercents,
            balance: 0
        });
        // console.log("Enrollment complete. First charity: %s, Percentage: %d", userTopic.charities[0], userTopic.charityPercents[0]);
    }

    function changeTopics(address user, string[] memory _topics) public onlyUserOrOwner(user) {
        require(_topics.length == 3, "Topics must be 3");
        
        UserTopics storage userTopic = topics[user];
        userTopic.ttopics = _topics;
    }

    // TODO: Automate this using ERC-20 and approve()

    function donate() public payable {
        topics[msg.sender].balance += msg.value;
        emit Donated(msg.sender, msg.value);
    }

    function withdraw() public {
        require(topics[msg.sender].balance > 0, "No balance to withdraw");

        // send money back to msg.sender
        payable(msg.sender).transfer(topics[msg.sender].balance);
        topics[msg.sender].balance = 0;
    }

    function updateProportion(address user, address charity, uint256 percentage) public onlyOwner {
        for (uint256 i; i < topics[user].charityPercents.length; i++) {
            if (topics[user].charities[i] == charity) {
                topics[user].charityPercents[i] = percentage;
                return;
            }
        }
        require(false, "Charity not enrolled");
    }

    function getTopics(address user) public view returns (string[] memory _topics) {
        return topics[user].ttopics;    
    }

    function addCharity(address user, address charity, uint256 percentage) public onlyOwner {
        topics[user].charities.push(charity);
        topics[user].charityPercents.push(percentage);
    }

    function splitAmongCharities(address user) public onlyOwner {
        uint256 totalBalance = topics[user].balance;
        topics[user].balance = 0;
        for (uint256 i; i < topics[user].charityPercents.length; i++) {
            address charity = topics[user].charities[i];
            uint256 percentage = topics[user].charityPercents[i];
            uint256 amount = totalBalance * percentage / 100;
            payable(charity).transfer(amount);
        }

        emit SplitAmongCharities(user, totalBalance);
    }

    function getBalance(address recipient) public view returns (uint256 balance) {
        return topics[recipient].balance;
    }

    function getUserTopics(address user) public view returns (
    string[] memory,
    address[] memory,
    uint256[] memory,
    uint256
    ) {
    UserTopics storage ut = topics[user];
    return (ut.ttopics, ut.charities, ut.charityPercents, ut.balance);
}

}   
