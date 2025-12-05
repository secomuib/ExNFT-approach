
// ================================================================
// Definitions
// ================================================================

// Validates that the environment has no ETH value and a valid sender
definition validEnv(env e) returns bool =
    e.msg.value == 0 && e.msg.sender != 0;

// Validates that a swap proposal has valid parameters:
// - Non-zero and distinct addresses
// - Non-zero and distinct token IDs
// - Both tokens are available for new proposals
definition validSwap(address from, address to, uint256 tokenId1, uint256 tokenId2, uint256 deadline, env e) returns bool =
    from != 0 && to != 0 && from != to &&
    tokenId1 != 0 && tokenId2 != 0 && tokenId1 != tokenId2 &&
    newProposal(tokenId1) == true && newProposal(tokenId2) == true;

// ================================================================
// Methods
// ================================================================

methods {
    function swapProposal(address, address, uint256, uint256, uint256) external;
    function acceptSwap(uint256, uint256) external;
    function rejectOrCancelSwap(uint256, uint256) external;

    function ownerOf(uint256) external returns (address) envfree;
    function getApproved(uint256) external returns (address) envfree;
    function isApprovedForAll(address, address) external returns (bool) envfree;

    function swapProp(uint256) external returns (address, address, uint256, uint256, uint256) envfree;
    function newProposal(uint256) external returns (bool) envfree;
}

// ================================================================
// Ghost Variables
// ================================================================
// Ghost variables track proposal state across transactions for verification

// Proposal created for a given tokenId
ghost mapping(uint256 => bool) ghostProposalCreated;

// Proposal caller for a given tokenId
ghost mapping(uint256 => address) ghostProposalCaller;

// Swap proposal accepted
ghost mapping(uint256 => bool) ghostSwapAccepted;

// Acceptance caller for a given tokenId
ghost mapping(uint256 => address) ghostAcceptanceCaller;

// Swap proposal cancelled or rejected
ghost mapping(uint256 => bool) ghostSwapCancelled;

// Cancellation caller for a given tokenId
ghost mapping(uint256 => address) ghostCancellationCaller;

// ================================================================
// Hooks
// ================================================================

// Hook to track SwapRequest events for non-repudiation verification
hook LOG4(uint offset, uint length, bytes32 eventSig, bytes32 caller, bytes32 tokenId1, bytes32 tokenId2) {
    // SwapRequest event signature: SwapRequest(address,uint256,uint256,address,address,uint256)
    bytes32 swapRequestdSig = to_bytes32(0x39a2fca053723c5b95854cc80b0ce4b052f01754d3aec7f40ba037c9aff9c37c);
    // AcceptSwap event signature: AcceptSwap(address,uint256,uint256,address,address)
    bytes32 acceptSwapSig = to_bytes32(0x7b25633ca2811df41400b397519b006fbcd81ad7cea8c2f6fbe847a8560f27dd); 
    // RejectOrCancelSwap event signature: RejectOrCancelSwap(address,uint256,uint256,address,address)
    bytes32 rejectOrCancelSwapSig = to_bytes32(0x723d14a9098ff5b7af4f61b230bfa05e72e19c050a27952b632517193044e866);

    if (eventSig == swapRequestdSig) {
        // SwapRequest event signature
        address caller_Address = require_address(caller);
        ghostProposalCreated[require_uint256(tokenId1)] = true;
        ghostProposalCaller[require_uint256(tokenId1)] = caller_Address;
    } else if (eventSig == acceptSwapSig) {
        // AcceptSwap event signature
        address caller_Address = require_address(caller);
        ghostSwapAccepted[require_uint256(tokenId1)] = true;
        ghostAcceptanceCaller[require_uint256(tokenId1)] = caller_Address;
    } else if (eventSig == rejectOrCancelSwapSig) {
        // RejectOrCancelSwap event signature
        address caller_Address = require_address(caller);
        ghostSwapCancelled[require_uint256(tokenId1)] = true;
        ghostCancellationCaller[require_uint256(tokenId1)] = caller_Address;
    }
}

// ================================================================
// Helper Functions
// ================================================================

// Check if a token has an active swap proposal
// Returns true if the proposal exists (from != 0) and hasn't expired yet
function isTokenPropOpened(env e, uint256 swapId) returns bool {
    address from;
    address to;
    uint256 token1;
    uint256 token2;
    uint256 deadline;

    from, to, token1, token2, deadline = swapProp(swapId);
    return from != 0 && deadline >= e.block.timestamp;
}

// Check if a user is authorized to operate on a token
function isAuthorized(env e, address user, uint256 tokenId) returns bool {
    address owner = ownerOf(tokenId);
    address approved = getApproved(tokenId);
    bool approvedForAll = isApprovedForAll(owner, user);

    return user == owner || user == approved || approvedForAll;
}

// Validate the initial setup parameters for swap are correct
function requireValidSwapSetup(
    env e,
    uint256 swapId,
    address from,
    address to,
    uint256 tokenId1,
    uint256 tokenId2,
    uint256 deadline
) {
    require validSwap(from, to, tokenId1, tokenId2, deadline, e);
    require swapId == tokenId1; // Assuming swapId is tokenId1

    address tokenId1Owner = ownerOf(tokenId1);
    address tokenId2Owner = ownerOf(tokenId2);

    require tokenId1Owner == from && tokenId1Owner != 0;
    require tokenId2Owner == to && tokenId2Owner != 0;
    require deadline > e.block.timestamp;
}

// Validate basic swap proposal parameters
function requireBasicProposalParams(
    address receiver,
    uint256 tokenId1,
    uint256 tokenId2,
    uint256 deadline,
    env e
) {
    require receiver != 0;
    require tokenId1 != 0;
    require tokenId2 != 0;
    require deadline > e.block.timestamp && deadline < max_uint256;
    require tokenId1 != tokenId2;
}

// Rule: correctOwnershipTransfer
// Verifies that swaps result in the correct final ownership
rule correctOwnershipTransfer(uint256 swapId) {
    env e;
    require validEnv(e);

    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    requireValidSwapSetup(e, swapId, fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial);

    // Execute Swap
    acceptSwap(e, tokenId1Initial, tokenId2Initial);

    address tokenId1OwnerFinal = ownerOf(tokenId1Initial);
    address tokenId2OwnerFinal = ownerOf(tokenId2Initial);

    // Both tokens have correct final owners
    assert tokenId1OwnerFinal == toInitial;
    assert tokenId2OwnerFinal == fromInitial;
}

// Rule: ownershipOrAllowanceProposal
// Ensures only authorized parties can propose swaps
rule ownershipOrAllowanceProposal() {
    env e;
    require validEnv(e);

    address receiver;
    uint256 tokenId1;
    uint256 tokenId2;
    uint256 deadline;

    requireBasicProposalParams(receiver, tokenId1, tokenId2, deadline, e);

    // Ensure the proposer is the owner of tokenId1
    address proposer = ownerOf(tokenId1);

    // Ensure the receiver is the owner of tokenId2
    require receiver == ownerOf(tokenId2);

    // Ensure receiver and owner are non-zero
    require receiver != 0;
    require proposer != 0;

    // Ensure proposer and receiver are distinct
    require proposer != receiver;

    // Verify that sender is authorized to propose the swap for tokenId1
    bool isAuthorized = isAuthorized(e, e.msg.sender, tokenId1);

    // tokenId1 must not have any opened swap proposals
    require !isTokenPropOpened(e, tokenId1) == true;

    // Propose Swap
    swapProposal@withrevert(e, proposer, receiver, tokenId1, tokenId2, deadline);
    bool succeeded = !lastReverted;

    // Swap proposal only succeeds if sender is authorized
    assert succeeded <=> isAuthorized;
}

// Rule: ownershipOrAllowanceAcceptance
// Ensures only authorized parties can accept swaps
rule ownershipOrAllowanceAcceptance() {
    env e;
    require validEnv(e);

    uint256 swapId;
    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    requireValidSwapSetup(e, swapId, fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial);

    // Verify that sender is authorized to accept the swap for tokenId2
    bool isAuthorized = isAuthorized(e, e.msg.sender, tokenId2Initial);

    // tokenId2 must not have any opened swap proposals
    require !isTokenPropOpened(e, tokenId2Initial);

    acceptSwap@withrevert(e, tokenId1Initial, tokenId2Initial);
    bool succeeded = !lastReverted;

    // Swap acceptance only succeeds if sender is authorized
    assert succeeded <=> isAuthorized;
}

// Rule: noTokenTheft
// A malicious actor (one of the swap parties) can only gain ownership
// of a token they didn't originally own if they lose ownership of their own token
rule noTokenTheft(uint256 swapId, method f) filtered { 
        f -> f.selector != sig:acceptTransfer(uint256).selector
    } {
    env e;
    require validEnv(e);

    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;
    address maliciousActor;

    require e.msg.sender == maliciousActor;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    requireValidSwapSetup(e, swapId, fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial);

    require maliciousActor == fromInitial || maliciousActor == toInitial; // Malicious actor is one of the swap parties
    require !isTokenPropOpened(e, tokenId2Initial); // Ensure tokenId2Initial doesn't have any opened swap proposals

    address tokenId1OwnerInitial = ownerOf(tokenId1Initial);
    address tokenId2OwnerInitial = ownerOf(tokenId2Initial);

    // Execute any function
    calldataarg args;
    if (f.selector == sig:acceptSwap(uint256,uint256).selector) {
        acceptSwap(e, tokenId1Initial, tokenId2Initial);
    } else {
        f(e, args);
    }

    address tokenId1OwnerFinal = ownerOf(tokenId1Initial);
    address tokenId2OwnerFinal = ownerOf(tokenId2Initial);

    // If malicious actor managed to gain ownership of one token, they must have lost ownership of the other token
    assert (maliciousActor != tokenId1OwnerInitial && maliciousActor == tokenId1OwnerFinal) =>
           (maliciousActor == tokenId2OwnerInitial && maliciousActor != tokenId2OwnerFinal);
}

// Rule: eventPersists
// Ensures that proposal evidence persists even after other contract operations
rule eventPersists(method f) filtered {
    f -> f.contract == currentContract
            && !f.isView
            // Exclude safeTransferFrom to avoid HAVOC from onERC721Received callbacks
            && f.selector != sig:safeTransferFrom(address,address,uint256).selector
            && f.selector != sig:safeTransferFrom(address,address,uint256,bytes).selector
} {
    env e;
    require validEnv(e);

    address proposer;
    address receiver;
    uint256 tokenId1;
    uint256 tokenId2;
    uint256 deadline;

    require proposer != 0;
    requireBasicProposalParams(receiver, tokenId1, tokenId2, deadline, e);

    address caller = e.msg.sender;
    swapProposal(e, proposer, receiver, tokenId1, tokenId2, deadline);

    calldataarg args;
    f(e, args);

    // Evidence of the swap proposal event still persists
    assert ghostProposalCreated[tokenId1];
    // Caller can not deny having created the proposal
    assert ghostProposalCaller[tokenId1] == caller;
}

// Rule: deadlineRespected
// Proposals cannot be accepted after they expire
rule deadlineRespected(uint256 swapId) {
    env e;
    require validEnv(e);

    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    requireValidSwapSetup(e, swapId, fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial);

    require !isTokenPropOpened(e, tokenId2Initial); // Ensure tokenId2Initial doesn't have any opened swap proposals
    require e.msg.sender == toInitial; // Only the 'to' address can accept the swap

    acceptSwap@withrevert(e, tokenId1Initial, tokenId2Initial);
    bool succeeded = !lastReverted;

    // acceptSwap only succeeds if current time is before deadline
    assert succeeded <=> (e.block.timestamp < deadlineInitial);
}

// Rule: proposalNonRepudiation
// Verifies that the proposer cannot deny having created a swap proposal
rule proposalNonRepudiation() {
    env e;
    require validEnv(e);

    address proposer;
    address receiver;
    uint256 tokenId1;
    uint256 tokenId2;
    uint256 deadline;

    require proposer != 0;
    requireBasicProposalParams(receiver, tokenId1, tokenId2, deadline, e);

    address caller = e.msg.sender;
    bool authorized = isAuthorized(e, caller, tokenId1);
    swapProposal(e, proposer, receiver, tokenId1, tokenId2, deadline);

    // Caller was authorized to propose the swap
    assert authorized;
    // Evidence of the swap proposal event still persists
    assert ghostProposalCreated[tokenId1];
    // Caller can not deny having created the proposal
    assert caller == ghostProposalCaller[tokenId1];
}

// Rule: acceptanceNonRepudiation
// Verifies that the receiver cannot deny having accepted a swap proposal
rule acceptanceNonRepudiation() {
    env e;
    require validEnv(e);

    uint256 swapId;
    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    requireValidSwapSetup(e, swapId, fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial);

    address caller = e.msg.sender;
    // Caller must be authorized to accept the swap for tokenId2
    bool authorized = isAuthorized(e, caller, tokenId2Initial);

    // tokenId2 must not have any opened swap proposals
    require !isTokenPropOpened(e, tokenId2Initial);

    acceptSwap(e, tokenId1Initial, tokenId2Initial);

    // Caller was authorized to accept the swap
    assert authorized;
    // Evidence of the swap acceptance event still persists
    assert ghostSwapAccepted[swapId];
    // Caller can not deny having accepted the swap
    assert caller == ghostAcceptanceCaller[swapId];
}

// Rule: cancellationNonRepudiation
// Verifies that the proposer or the receiver cannot deny having cancelled or rejected an opened swap proposal
rule cancellationNonRepudiation() {
    env e;
    require validEnv(e);

    uint256 swapId;
    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    requireValidSwapSetup(e, swapId, fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial);

    address caller = e.msg.sender;
    require isAuthorized(e, caller, tokenId1Initial) || isAuthorized(e, caller, tokenId2Initial);

    rejectOrCancelSwap(e, tokenId1Initial, tokenId2Initial);

    // Evidence of the swap cancellation/rejection event still persists
    assert ghostSwapCancelled[swapId];
    // Caller can not deny having cancelled or rejected the swap
    assert caller == ghostCancellationCaller[swapId];
}

// Rule: selectiveReception
// Ensure that the receiver must explicitly accept the swap to successfully transfer the tokens ownership
rule selectiveReception(uint256 swapId, method f) filtered {
    f -> f.selector != sig:acceptTransfer(uint256).selector
} {
    env e;
    require validEnv(e);

    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    requireValidSwapSetup(e, swapId, fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial);

    address tokenId1OwnerInitial = ownerOf(tokenId1Initial);
    address tokenId2OwnerInitial = ownerOf(tokenId2Initial);

    // Execute any function
    calldataarg args;
    f(e, args);

    address tokenId1OwnerFinal = ownerOf(tokenId1Initial);
    address tokenId2OwnerFinal = ownerOf(tokenId2Initial);
    
    // Both tokens have swapped owners
    assert (tokenId1OwnerFinal != tokenId1OwnerInitial) => f.selector == sig:acceptSwap(uint256,uint256).selector;
    assert (tokenId2OwnerFinal != tokenId2OwnerInitial) => f.selector == sig:acceptSwap(uint256,uint256).selector;
}

// Rule: selectiveAcceptance
// Verifies that when multiple swap proposals exists for the same tokenId, the receiver must 
// selectively reject the unwanted proposals and accept the desired one 
rule selectiveAcceptance(uint256 swapId1, uint256 swapId2) {
    env e;
    require validEnv(e);

    address fromInitial1;
    address toInitial1;
    uint256 tokenId1Initial1;
    uint256 tokenId2Initial1;
    uint256 deadlineInitial1;

    address fromInitial2;
    address toInitial2;
    uint256 tokenId1Initial2;
    uint256 tokenId2Initial2;
    uint256 deadlineInitial2;

    fromInitial1, toInitial1, tokenId1Initial1, tokenId2Initial1, deadlineInitial1 = swapProp(swapId1);
    requireValidSwapSetup(e, swapId1, fromInitial1, toInitial1, tokenId1Initial1, tokenId2Initial1, deadlineInitial1);

    fromInitial2, toInitial2, tokenId1Initial2, tokenId2Initial2, deadlineInitial2 = swapProp(swapId2);
    requireValidSwapSetup(e, swapId2, fromInitial2, toInitial2, tokenId1Initial2, tokenId2Initial2, deadlineInitial2);

    address tokenId1OwnerInitial1 = ownerOf(tokenId1Initial1);
    address tokenId2OwnerInitial1 = ownerOf(tokenId2Initial1);

    address tokenId1OwnerInitial2 = ownerOf(tokenId1Initial2);
    address tokenId2OwnerInitial2 = ownerOf(tokenId2Initial2);

    require swapId1 != swapId2 && fromInitial1 != fromInitial2 && tokenId1Initial1 != tokenId1Initial2; // Ensure different swaps
    require toInitial1 == toInitial2 && tokenId2Initial1 == tokenId2Initial2; // Same receiver and tokenId2 
    require isAuthorized(e, e.msg.sender, tokenId2Initial1); // Sender is authorized to accept the swap for tokenId2
    require !isTokenPropOpened(e, tokenId2Initial1); // Ensure tokenId2OwnerInitial doesn't have opened any swap proposal

    storage initialState = lastStorage;

    // Attempt to accept swapId1 
    acceptSwap@withrevert(e, tokenId1Initial1, tokenId2Initial1);
    bool succeeded1 = !lastReverted;

    // Attempt to accept swapId2
    acceptSwap@withrevert(e, tokenId1Initial2, tokenId2Initial2) at initialState;
    bool succeeded2 = !lastReverted;


    assert succeeded1 && succeeded2; // Receiver can selectively accept both swaps

}

// Rule: atomicSwap
// Ensures atomicity - both tokens swap owners together or neither does
rule atomicSwap(uint256 swapId) {
    env e;
    require validEnv(e);

    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    requireValidSwapSetup(e, swapId, fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial);

    address tokenId1OwnerInitial = ownerOf(tokenId1Initial);
    address tokenId2OwnerInitial = ownerOf(tokenId2Initial);

    // Execute Swap
    acceptSwap(e, tokenId1Initial, tokenId2Initial);

    address tokenId1OwnerFinal = ownerOf(tokenId1Initial);
    address tokenId2OwnerFinal = ownerOf(tokenId2Initial);

    // Both tokens have swapped owners
    assert (tokenId1OwnerFinal != tokenId1OwnerInitial) => (tokenId2OwnerFinal != tokenId2OwnerInitial);
    assert (tokenId2OwnerFinal != tokenId2OwnerInitial) => (tokenId1OwnerFinal != tokenId1OwnerInitial);
}

// Rule: nonPartialExecution
// If the swap succeeds, both tokens must change ownership
// If the swap fails, both tokens must retain their original owners
rule nonPartialExecution(uint256 swapId) {
    env e;
    require validEnv(e);

    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    requireValidSwapSetup(e, swapId, fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial);

    address tokenId1OwnerInitial = ownerOf(tokenId1Initial);
    address tokenId2OwnerInitial = ownerOf(tokenId2Initial);

    acceptSwap@withrevert(e, tokenId1Initial, tokenId2Initial);
    bool succeeded = !lastReverted;

    if (succeeded) {
        address tokenId1OwnerFinal = ownerOf(tokenId1Initial);
        address tokenId2OwnerFinal = ownerOf(tokenId2Initial);

        // Both tokens have swapped owners
        assert (tokenId1OwnerFinal != tokenId1OwnerInitial) => (tokenId2OwnerFinal != tokenId2OwnerInitial);
        assert (tokenId2OwnerFinal != tokenId2OwnerInitial) => (tokenId1OwnerFinal != tokenId1OwnerInitial);
    }
    else {
        // If acceptSwap fails, both tokens retain their original owners
        address tokenId1OwnerFinal = ownerOf(tokenId1Initial);
        address tokenId2OwnerFinal = ownerOf(tokenId2Initial);

        assert tokenId1OwnerFinal == tokenId1OwnerInitial;
        assert tokenId2OwnerFinal == tokenId2OwnerInitial;
    }
}

// Rule: symmetricCancellation
// Ensures both parties have equal rights to cancel/reject proposals
rule symmetricCancellation(uint256 swapId) {
    env e1;
    env e2;

    require validEnv(e1);
    require validEnv(e2);
    require e1.block.timestamp == e2.block.timestamp; // Both envs represent the same point in time

    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    requireValidSwapSetup(e1, swapId, fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial);

    require !isTokenPropOpened(e1, tokenId2Initial); // Ensure tokenId2Initial doesn't have any opened swap proposals

    // Store state before cancellation/rejection attempts
    storage initialState = lastStorage;

    // Cancellation by proposer (token1's owner)
    require e1.msg.sender == fromInitial;
    rejectOrCancelSwap@withrevert(e1, tokenId1Initial, tokenId2Initial) at initialState;
    bool proposerCanCancel = !lastReverted;
    assert isTokenPropOpened(e1, swapId) == false;

    // Rejection by receiver (token2's owner)
    require e2.msg.sender == toInitial;
    rejectOrCancelSwap@withrevert(e2, tokenId1Initial, tokenId2Initial) at initialState;
    bool receiverCanReject = !lastReverted;
    assert isTokenPropOpened(e2, swapId) == false;

    // Both parties can successfully cancel/reject the swap
    assert proposerCanCancel == receiverCanReject;
}
