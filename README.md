# Fair and Direct Exchange of Non-Fungible Tokens: the ExNFT approach

A Proof of Concept implementation for the Fair and Direct Exchange of Non-Fungible Tokens: the ExNFT approach.

## Prerequisites
- Node.js (v16 or higher recommended)
- Yarn package manager
- Hardhat development environment
- Certora Verification Language LSP

## Install dependencies and deployment

### Environment Configuration
Create an .env file with the following variables:

    `MNEMONIC=<wallet-mnemonic>`

    `COINMARKETCAP_API_KEY=<api-key>`

    `INFURA_API_KEY=<infura-api-key>`

    `ETHERSCAN_API_KEY=<etherscan-api-key>`

### Install dependencies

```
yarn install
```

## Testing

### Unit Tests

Run RejNFT contract tests:
```
npm run test
```

Run ExNFT contract tests:
```
npm run test:ExNFT
```

## Formal Verification with Certora Prover

1. Sign up in [Certora Prover](https://www.certora.com/prover) and obtain a personal access key.

2. Set the personal access key as an environment variable:

```
export CERTORAKEY=<personal_access_key>
```

3. Run verifications:

```
npm run test:verifier
```