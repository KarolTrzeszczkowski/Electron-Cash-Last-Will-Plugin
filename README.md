# Last Will plugin for Electron Cash
![logo](/pictures/licho_logo.png)
## Description
Last Will plugin is made for creation and management of the Last Will smart contract directly from a desktop Electron Cash.

### Features:

* Made on **BCH** chain,
* Security level of **cold storage**,
* Noncustodial,
* Permission-less,
* Implements a [dead man's switch](https://en.wikipedia.org/wiki/Dead_man%27s_switch) with a **6 months will trigger**,
* If you don't refresh your Last Will contract for 6 months, funds become available for your inheritor,
* **One-click** refreshing from a **hot wallet**,
* Refreshing wallet **can't access** your funds,
* You can always access your funds from a **cold wallet**.


## Contract description

Last Will smart contract uses the first working implementation of **looping transactions** <sup>[1](https://honest.cash/pein_sama/spending-constraints-with-op_checkdatasig-172) [2](https://tobiasruck.com/content/lets-play-chess-on-bch/)</sup> for refreshing the contract.

### Smart contract basics
The contract is defined by a special address that is cryptographically determined by the contract itself. [Learn more](https://en.bitcoin.it/wiki/Pay_to_script_hash). Funds are "in the contract" when they are sent to this special address. 

A contract consists of challenges, requirements that have to be met to access the funds stored in it.


### The Last Will contract
There are three challenges for the Last Will contract. 
Pseudo-code below shows the idea behind the smart contract:
```
contract LastWill()
{
    challenge refresh()
    {
        verify if the transaction 
        was signed by the creators refreshing wallet
        
        verify if the transaction 
        send all funds from the contract address
        back to the same contract address
    }
    
    challenge cold()
    {
        verify if the transaction 
        was signed by the creators cold wallet
     }
     
    challenge inheritor()
    {
        verify if the transaction 
        was signed by the inheritors wallet

        verify if 6 months have passed 
        since the funds were sent to the contract
    }
}
```
*refreshing* challenge sends funds from the contract back to the contract, effectively **resetting the timer** that *inheritor* challenge measures.

*inheritor* challenge lets your inheritor collect the money from the contract when the money age reaches 6 months.

*cold* challenge lets you spend your funds any time you like.

Contract security model relies on the certainty that the refreshing wallet can do you no harm, even if it's private key is stolen. Refreshing the contract is relatively frequent activity therefore it should not bring any risk. Even if you find yourself on the run, and the only computer available in an old pc in an algierian library, you should be able to send your contract a message **"I'm still alive"** safely and irrepressibly, without any risk of losing funds due to that. 

If your refreshing wallet get stolen, the only thing that the attacker can do is to refresh your contract, reset your timer. You can then end the contract from your cold wallet and create another one, with the different refreshing wallet. If you die with your refreshing key stolen, funds are not stolen. Your inheritor might never get the inheritance. So the actual worse case scenario is an expected result of simply **not using** the Last Will contract at all [(see Quadriga exchange story)](https://www.bbc.com/news/world-us-canada-47203706) or using the conventional, custodial and trusted last will and testament solutions.

Smart contract is not a standard transaction. To see it with your wallet you need the plugin.

Full code of the contract written with [spedn](https://spedn.readthedocs.io/en/latest/index.html) language can be found [here](LastWill.spedn)

## Refresh lock

There is a lock for refreshing, you can't do it for the first 7 days after creation or refreshing of the contract, so that no one, who have stolen your refreshing wallet can drain your funds to transaction fees by refreshing it a million times, over and over.

## Installing the plugin
Dirst, download and verify the last-will-plugin-vVERSION.zip file from [relesases](https://github.com/KarolTrzeszczkowski/Electron-Cash-Last-Will-Plugin/releases). Then go to your Electron Cash and install the plugin.
![install](/pictures/installing.png)
![add](/pictures/add_plugin.png)
The plugin will appear as one of the tabs.


## Creating a Last Will contract
In the plugin tab you will see three buttons.
![intro](/pictures/intro.png)
Click *Create Last Will contract* to create a new contract.
Fill the fields.
![creating](/pictures/creating.png)

## Licho Notification Service

The creator of this software Karol Trzeszczkowski (Licho) provides an optional e-mail notification service, that you can order through the plugin.

6 months is quite a **long period of time**, it's possible to forget about refreshing your contract. To solve this problem Licho offers the **notification service**. For a small fee Licho will send you an **e-mail reminder** a week before your contract expiry date.

The notification service is also a solution to the issue, that a wallet without the plugin installed can't see the contract. This means that your inheritor won't know about the contract unless they checked. When you pass away and your contract expire, Licho may **let your inheritor know** about the Last Will contract waiting to be claimed.

If you decide to order an e-mail notification, a transaction will be created. It will be of the value of the fee for the services and it will have an encrypted email address attached as the OP_RETURN data. For the inheritor notification, an encrypted e-mail and the contract address will be attached. 

## Refreshing the contract

## Ending the contract

## Inheriting

## License

This software is distributed on GPL v3 license. The author encourage you to build your own smart contract plugins based on Last Will plugin code, implement desired functions and submit a pull request to this repository or fork this project and compete, if I fail to deliver what you expect. Just remember to publish your improvements on the same license.

## Donations

The best form of support is **using** this plugin and notification service. If you wish to support Licho the other way, consider donating to the following addresses:

Cash Account: Karol#567890

bitcoincash:qq93dq0j3uez8m995lrkx4a6n48j2fckfuwdaqeej2

Legacy format: 121dPy31QTsxAYUyGRbwEmW2c1hyZy1Xnz

![donate](/pictures/donate.png)













