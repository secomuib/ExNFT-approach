// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.12;

import "./RejNFT.sol";
import "./interfaces/IRejNFT.sol";
import "./interfaces/IExNFT.sol";

contract ExNFT is RejNFT, IExNFT {

    struct proposal{
        address from;
        address to;
        uint256 tokenId1;
        uint256 tokenId2;
        uint256 deadline;
    }

    mapping(uint256 => proposal) public swapProp;
    mapping(uint256 => bool) public newProposal;
    
    constructor (string memory name_, string memory symbol_)
        RejNFT(name_, symbol_) 
        { }




    /**
     * @dev Transfers `tokenId` from `from` to `to`.
     *  As opposed to {transferFrom}, this imposes no restrictions on msg.sender.
     *
     * Requirements:
     *
     * - `to` cannot be the zero address.
     * - `tokenId` token must be owned by `from`.
     *
     * Emits a {TransferRequest} event.
     */
    function swapProposal(
        address from,
        address to,
        uint256 tokenId1,
        uint256 tokenId2,
        uint256 deadline
    ) public virtual {
        require(
            _isAuthorized(from, _msgSender(), tokenId1),
            "ExNFT: transfer caller is not owner nor approved"
        );

        require(swapProp[tokenId1].from == address(0) || swapProp[tokenId1].deadline < block.timestamp, 
                "ExNFT: can't open swap proposal");
        
        require(
            from != address(0) && ownerOf(tokenId1) == from,
            "ExNFT: transfer from incorrect owner"
        );
        require(
            to != address(0) && ownerOf(tokenId2) == to,
            "ExNFT: transfer to incorrect owner"
        );
        require(deadline > block.timestamp, "ExNFT: Incorrect deadline");

        // Clear approvals from the previous owner
        _approve(address(0), tokenId1, from, false);

        swapProp[tokenId1] = proposal(from, to, tokenId1, tokenId2, deadline);
        newProposal[tokenId1] = true;
        newProposal[tokenId2] = true;

        emit SwapRequest(msg.sender, tokenId1, tokenId2, from, to, deadline);
    }


    function acceptSwap(uint256 tokenId1, uint256 tokenId2) public {
        require(newProposal[tokenId2], "ExNFT: Any swap proposal for the provided token");
        
        require(swapProp[tokenId1].tokenId2 == tokenId2, "ExNFT: any swap proposal for $tokenId1$ provided or the swap proposal for $tokenId2$ does not correspond with the given $tokenId2$");

        require(
            _isAuthorized(ownerOf(tokenId2), _msgSender(), tokenId2),
            "ExNFT: the caller is neither the receiver nor approved for the token"
        );

        require(block.timestamp < swapProp[tokenId1].deadline, "ExNFT: Deadline expired");

        require(swapProp[tokenId2].from == address(0) || swapProp[tokenId2].deadline < block.timestamp, "ExNFT: can't accept swap tokenId2 must cancel their opened swap proposal");

        address from = swapProp[tokenId1].from;
        address to = swapProp[tokenId1].to;

        _owners[tokenId1] = to; 
        emit Transfer(from, to, tokenId1);

        // Clear approvals from the previous owner
        _approve(address(0), tokenId1, address(0), false);

        
        _owners[tokenId2] = from;
        emit Transfer(to, from, tokenId2);
        
        delete swapProp[tokenId1];
        newProposal[tokenId1] = false;
        newProposal[tokenId2] = false;

        emit AcceptSwap(msg.sender, tokenId1, tokenId2, from, to);
    }

    function rejectOrCancelSwap(uint256 tokenId1, uint256 tokenId2) public {
        require(newProposal[tokenId1] && newProposal[tokenId2], "ExNFT: Any swap proposal for the provided tokens currently open");
        
        address from = swapProp[tokenId1].from;
        address to = swapProp[tokenId1].to;

        require(
            (_isAuthorized(from, _msgSender(), tokenId1) || _isAuthorized(to,_msgSender(), tokenId2)) &&
            swapProp[tokenId1].tokenId1 == tokenId1 &&  swapProp[tokenId1].tokenId2 == tokenId2,
            "ExNFT: reject transfer caller is not the receiver or the sender nor approved of the token"
        );
        

        delete swapProp[tokenId1];
        newProposal[tokenId1] = false;
        newProposal[tokenId2] = false;

        emit RejectOrCancelSwap(msg.sender, tokenId1, tokenId2, from, to);
    }
}