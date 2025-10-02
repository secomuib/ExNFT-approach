// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

import "./NFT.sol";
import "./interfaces/IRejNFT.sol";

contract RejNFT is ERC721, IRejNFT, Ownable {

    uint256 private _tokenIdCounter;

    // Mapping from token ID to transferable owner
    mapping(uint256 => address) internal _transferableOwners;

    /**
     * @dev Initializes the contract by setting a `name` and a `symbol` to the token collection.
     * overrides ERC721 constructor
     */

    constructor (string memory name_, string memory symbol_) ERC721(name_, symbol_) Ownable(msg.sender){}
    
    /**
     * @dev Transfers `tokenId` from its current owner to `to`, or alternatively mints (or burns) if the current owner
     * (or `to`) is the zero address. Returns the owner of the `tokenId` before the update.
     *
     * The `auth` argument is optional. If the value passed is non 0, then this function will check that
     * `auth` is either the owner of the token, or approved to operate on the token (by the owner).
     *
     * Emits a {Transfer} event.
     *
     * NOTE: If overriding this function in a way that tracks balances, see also {_increaseBalance}.
     */
    function _update(address to, uint256 tokenId) internal virtual returns (address) {
        address from = _ownerOf(tokenId);
        
        unchecked {
                _transferableOwners[tokenId] = to;
        }

        emit TransferRequest(from, to, tokenId);

        return from;
    }

    /// @inheritdoc IERC721
    function transferFrom(address from, address to, uint256 tokenId) public virtual override(ERC721, IERC721) {
        if (!_isAuthorized(ownerOf(tokenId), msg.sender, tokenId)) {
            revert ERC721InsufficientApproval(ownerOf(tokenId), tokenId);
        }
        if (to == address(0)) {
            revert ERC721InvalidReceiver(address(0));
        }
        // Setting an "auth" arguments enables the `_isAuthorized` check which verifies that the token exists
        // (from != 0). Therefore, it is not needed to verify that the return value is not 0 here.
        address previousOwner = _update(to, tokenId);
        if (previousOwner != from) {
            revert ERC721IncorrectOwner(from, tokenId, previousOwner);
        }
    }

    /**
     * @dev Mints `tokenId` and transfers it to `to`.
     *
     * WARNING: Usage of this method is discouraged, use {_safeMint} whenever possible
     *
     * Requirements:
     *
     * - `tokenId` must not exist.
     * - `to` cannot be the zero address.
     *
     * Emits a {Transfer} event.
     */
    function _mintProposal(address to, uint256 tokenId) internal {
        if (to == address(0)) {
            revert ERC721InvalidReceiver(address(0));
        }
        address previousOwner = _update(to, tokenId);
        if (previousOwner != address(0)) {
            revert ERC721InvalidSender(address(0));
        }
    }

    /// @inheritdoc IERC721
    function ownerOf(uint256 tokenId) public view virtual override(ERC721, IERC721) returns (address) {
        return _owners[tokenId];
    }

    //-------------------------------------------------------------------------------//
    //                                Added functions                                //
    //-------------------------------------------------------------------------------//

    /**
     * @dev Safely mints a new token and transfers it to `to`.
     * The new tokenId is consecutive with the last token minted. 
     */
    function safeMint(address _to) public virtual onlyOwner {
        uint256 tokenId = _tokenIdCounter;
        _tokenIdCounter++;
        _mintProposal(_to, tokenId);
    }

    /**
     * @dev Returns the address of `tokenId` to which it is currently offered.
     *
     */
    function transferableOwnerOf(uint256 tokenId)
        public
        view
        virtual
        override
        returns (address)
    {
        address owner = _transferableOwners[tokenId];

        return owner;
    }

    /**
     * @dev `tokenId` transferableOwner accepts `tokenId`transfer.
     * The transfer of `tokenId`to the transferableOwner is executed.
     *
     * Requirements:
     *
     * - `_msgSender` must be the `tokenId` transferable Owner.
     *
     * Emits a {Transfer} event.
     */
    function acceptTransfer(uint256 tokenId) public virtual override {
        require(
            _transferableOwners[tokenId] == _msgSender(),
            "RejNFT: accept transfer caller is not the receiver of the token"
        );

        address from = ownerOf(tokenId);
        address to = _msgSender();

        if (from != address(0)) {
            // Perhaps previous owner is address(0), when minting
            _balances[from] -= 1;
        }
        _balances[to] += 1;
        _owners[tokenId] = to;

        // remove the transferable owner from the mapping
        _transferableOwners[tokenId] = address(0);

        emit Transfer(from, to, tokenId);
    }

    /**
     * @dev `tokenId` transferableOwner rejects `tokenId` transfer.
     * The `tokenId`transferableOwner is set to addressZero.
     *
     * Requirements:
     *
     * - `_msgSender` must be the `tokenId` transferable Owner.
     *
     * Emits a {RejectTransfer} event.
     */
    function rejectTransfer(uint256 tokenId) public virtual {
        require(
            _transferableOwners[tokenId] == _msgSender(),
            "RejNFT: reject transfer caller is not the receiver of the token"
        );

        address from = ownerOf(tokenId);
        address to = _msgSender();

        _transferableOwners[tokenId] = address(0);

        emit RejectTransfer(from, to, tokenId);
    }

    /**
     * @dev `tokenId` owner cencels a `tokenId` transfer request.
     * The `tokenId`transferableOwner is set to addressZero.
     *
     * Requirements:
     *
     * - `tokenId` can be non minted: `tokenId` must be addressZero and `_msgSender` must be the RejectableNFT smart contract owner.
     * - ``_msgSender must have `tokenId` approval or must be `tokenId` owner
     *
     * Emits a {CancelTransfer} event.
     */
    function cancelTransfer(uint256 tokenId) public virtual override {
        //solhint-disable-next-line max-line-length
        require(
            // perhaps previous owner is address(0), when minting
            (ownerOf(tokenId) == address(0) &&
                owner() == _msgSender()) ||
                _isAuthorized(ownerOf(tokenId), _msgSender(), tokenId),
            "ERC721: transfer caller is not owner nor approved"
        );

        address from = ownerOf(tokenId);
        address to = _transferableOwners[tokenId];

        require(to != address(0), "RejNFT: token is not transferable");
        _transferableOwners[tokenId] = address(0);

        emit CancelTransfer(from, to, tokenId);
    }


    /**
     * @dev Hook that is called before any token transfer. This includes minting and burning. If {ERC721Consecutive} is
     * used, the hook may be called as part of a consecutive (batch) mint, as indicated by `batchSize` greater than 1.
     *
     * Calling conditions:
     *
     * - When `from` and `to` are both non-zero, ``from``'s tokens will be transferred to `to`.
     * - When `from` is zero, the tokens will be minted for `to`.
     * - When `to` is zero, ``from``'s tokens will be burned.
     * - `from` and `to` are never both zero.
     * - `batchSize` is non-zero.
     *
     * To learn more about hooks, head to xref:ROOT:extending-contracts.adoc#using-hooks[Using Hooks].
     */
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 firstTokenId
    ) internal virtual {}

    /**
     * @dev Hook that is called after any token transfer. This includes minting and burning. If {ERC721Consecutive} is
     * used, the hook may be called as part of a consecutive (batch) mint, as indicated by `batchSize` greater than 1.
     *
     * Calling conditions:
     *
     * - When `from` and `to` are both non-zero, ``from``'s tokens were transferred to `to`.
     * - When `from` is zero, the tokens were minted for `to`.
     * - When `to` is zero, ``from``'s tokens were burned.
     * - `from` and `to` are never both zero.
     * - `batchSize` is non-zero.
     *
     * To learn more about hooks, head to xref:ROOT:extending-contracts.adoc#using-hooks[Using Hooks].
     */
    function _afterTokenTransfer(
        address from,
        address to,
        uint256 firstTokenId
    ) internal virtual {}

}