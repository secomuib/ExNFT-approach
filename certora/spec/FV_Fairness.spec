

definition validEnv(env e) returns bool = e.msg.value == 0 && e.msg.sender != 0;
definition validSwap(address from, address to, uint256 tokenId1, uint256 tokenId2, uint256 deadline, env e) returns bool = from != 0 && to != 0 && from != to && tokenId1 != 0 && tokenId2 != 0 && tokenId1 != tokenId2 && newProposal(e, tokenId1) == true && newProposal(e, tokenId2) == true;

methods {
    function swapProposal(address, address, uint256, uint256, uint256) external;
    function acceptSwap(uint256, uint256) external;
    function rejectOrCancelSwap(uint256, uint256) external;
    
    function ownerOf(uint256) external returns (address) envfree;
    function getApproved(uint256) external returns (address) envfree;
    function isApprovedForAll(address, address) external returns (bool) envfree;

    function swapProp(uint256) external returns (address, address, uint256, uint256, uint256) envfree;
}

function isTokenPropOpened(env e, uint256 swapId) returns bool {
    address from;
    address to;
    uint256 token1;
    uint256 token2;
    uint256 deadline;
    
    from, to, token1, token2, deadline = swapProp(swapId);
    return from != 0 && deadline >= e.block.timestamp;
}

function isAuthorized(env e, address user, uint256 tokenId) returns bool {
    address owner = ownerOf(tokenId);
    address approved = getApproved(tokenId);
    bool approvedForAll = isApprovedForAll(owner, user);

    return user == owner || user == approved || approvedForAll;
}


/***
    * OWNERSHIP OR ALLOWANCE RULE: 
    * Owner or approved are the only ones allowed to propose the swap. 
    ***/
rule ownershipOrAllowanceProposal(){
    env e; 
    require validEnv(e);

    address receiver;
    uint256 tokenId1;
    uint256 tokenId2;
    uint256 deadline;

    require receiver != 0;
    require tokenId1 != 0;
    require tokenId2 != 0;
    require deadline > e.block.timestamp;
    require tokenId1 != tokenId2;

    //Verify that sender is authorized to propose the swap for nft1
    bool isAuthorized = isAuthorized(e, e.msg.sender, tokenId1);

    //tokenId1 must not have any opened swap proposals
    require !isTokenPropOpened(e, tokenId1) == true;

    //Propose Swap
    swapProposal@withrevert(e, e.msg.sender, receiver, tokenId1, tokenId2, deadline);
    bool succeeded = !lastReverted;

    //Swap proposal only succeeds if sender is authorized
    assert succeeded <=> isAuthorized;
}

/***
    * OWNERSHIP OR ALLOWANCE RULE: 
    * Owner or approved are the only ones allowed to accept the swap. 
    ***/
rule ownershipOrAllowanceAcceptance(){
     env e;
    require validEnv(e);

    //Initial state
    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;
    uint256 swapId;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    require validSwap(fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial, e);
    require swapId == tokenId1Initial; //Assuming swapId is tokenId1

    address tokenId1OwnerInitial = ownerOf(tokenId1Initial);
    address tokenId2OwnerInitial = ownerOf(tokenId2Initial);

    require tokenId1OwnerInitial == fromInitial && tokenId1OwnerInitial != 0;
    require tokenId2OwnerInitial == toInitial && tokenId2OwnerInitial != 0;
    require deadlineInitial > e.block.timestamp;

    //Verify that sender is authorized to accept the swap for nft2
    bool isAuthorized = isAuthorized(e, e.msg.sender, tokenId2Initial);

    //tokenId2 must not have any opened swap proposals
    require !isTokenPropOpened(e, tokenId2Initial);

    acceptSwap@withrevert(e, tokenId1Initial, tokenId2Initial);
    bool succeeded = !lastReverted;

    //Swap acceptance only succeeds if sender is authorized
    assert succeeded <=> isAuthorized;
}

/***
    * ATOMIC SWAP RULE: 
    * Both NFTs must have swapped owners or any must have owner transfer.
    *
***/
rule atomicSwap(uint256 swapId){
    env e;

    require validEnv(e);

    //Initial state
    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    require validSwap(fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial, e);
    require swapId == tokenId1Initial; //Assuming swapId is tokenId1

    address tokenId1OwnerInitial = ownerOf(tokenId1Initial);
    address tokenId2OwnerInitial = ownerOf(tokenId2Initial);

    require tokenId1OwnerInitial == fromInitial && tokenId1OwnerInitial != 0;
    require tokenId2OwnerInitial == toInitial && tokenId2OwnerInitial != 0;
    require deadlineInitial > e.block.timestamp;

    //Execute Swap
    acceptSwap(e, tokenId1Initial, tokenId2Initial);

    address tokenId1OwnerFinal = ownerOf(tokenId1Initial);
    address tokenId2OwnerFinal = ownerOf(tokenId2Initial);

    //Both NFTs have swapped owners
    assert (tokenId1OwnerFinal != tokenId1OwnerInitial) => (tokenId2OwnerFinal != tokenId2OwnerInitial);
    assert (tokenId2OwnerFinal != tokenId2OwnerInitial) => (tokenId1OwnerFinal != tokenId1OwnerInitial);
}

/***
    * CORRECT OWNERSHIP TRANSFER RULE: 
    * After acceptSwap, both NFTs must have the correct new owners.
    *
***/
rule correctOwnershipTransfer(uint256 swapId){
    env e;

    require validEnv(e);

    //Initial state
    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    require validSwap(fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial, e);
    require swapId == tokenId1Initial; //Assuming swapId is tokenId1

    address tokenId1OwnerInitial = ownerOf(tokenId1Initial);
    address tokenId2OwnerInitial = ownerOf(tokenId2Initial);

    require tokenId1OwnerInitial == fromInitial && tokenId1OwnerInitial != 0;
    require tokenId2OwnerInitial == toInitial && tokenId2OwnerInitial != 0;
    require deadlineInitial > e.block.timestamp;

    //Execute Swap
    acceptSwap(e, tokenId1Initial, tokenId2Initial);

    address tokenId1OwnerFinal = ownerOf(tokenId1Initial);
    address tokenId2OwnerFinal = ownerOf(tokenId2Initial);

    //Both NFTs have correct final owners
    assert tokenId1OwnerFinal == toInitial;
    assert tokenId2OwnerFinal == fromInitial;
}

/***
    * NON-PARTIAL EXECUTION RULE:
    * The swap must either fully succeed or fully fail, no partial execution.
    *
***/
rule nonPartialExecution(uint256 swapId){
    env e;
    require validEnv(e);

    //Initial state
    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    require validSwap(fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial, e);
    require swapId == tokenId1Initial; //Assuming swapId is tokenId1

    address tokenId1OwnerInitial = ownerOf(tokenId1Initial);
    address tokenId2OwnerInitial = ownerOf(tokenId2Initial);

    require tokenId1OwnerInitial == fromInitial && tokenId1OwnerInitial != 0;
    require tokenId2OwnerInitial == toInitial && tokenId2OwnerInitial != 0;
    require deadlineInitial > e.block.timestamp;

    
    acceptSwap@withrevert(e, tokenId1Initial, tokenId2Initial);
    bool succeeded = !lastReverted;

    if (succeeded){
        address tokenId1OwnerFinal = ownerOf(tokenId1Initial);
        address tokenId2OwnerFinal = ownerOf(tokenId2Initial);

        //Both NFTs have swapped owners
        assert (tokenId1OwnerFinal != tokenId1OwnerInitial) => (tokenId2OwnerFinal != tokenId2OwnerInitial);
        assert (tokenId2OwnerFinal != tokenId2OwnerInitial) => (tokenId1OwnerFinal != tokenId1OwnerInitial);
    }
    else  {
        //If acceptSwap fails, both NFTs retain their original owners
        address tokenId1OwnerFinal = ownerOf(tokenId1Initial);
        address tokenId2OwnerFinal = ownerOf(tokenId2Initial);

        assert tokenId1OwnerFinal ==  tokenId1OwnerInitial;
        assert tokenId2OwnerFinal ==  tokenId2OwnerInitial;
    }   
}

/***
    * DEADLINE RESPECT RULE:
    * The swap can only be accepted before the deadline. Expired swaps must not be accepted.
    *
***/
rule deadlineRespected(uint256 swapId){
    env e;
    require validEnv(e);

    //Initial state
    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    require validSwap(fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial, e);
    require swapId == tokenId1Initial; //Assuming swapId is tokenId1
    
    require !isTokenPropOpened(e, tokenId2Initial); // ensure tokenId2Initial doesn't have any opened swap proposals
    require e.msg.sender == toInitial; // only the 'to' address can accept the swap

    address tokenId1OwnerInitial = ownerOf(tokenId1Initial);
    address tokenId2OwnerInitial = ownerOf(tokenId2Initial);

    require tokenId1OwnerInitial == fromInitial && tokenId1OwnerInitial != 0;
    require tokenId2OwnerInitial == toInitial && tokenId2OwnerInitial != 0;

    acceptSwap@withrevert(e, tokenId1Initial, tokenId2Initial);
    bool succeeded = !lastReverted;
    assert succeeded <=> (e.block.timestamp < deadlineInitial); // acceptSwap only succeeds if current time is before deadline
}

/***
    * SIMETRIC RIGHT OF REJECTION/CANCELLATION RULE:
    * Both parties have the right to reject or cancel the swap proposal before it is accepted.
    *
***/
rule symmetricCancellation(uint256 swapId){
    env e1;
    env e2;

    require validEnv(e1);
    require validEnv(e2);

    require e1.block.timestamp == e2.block.timestamp; // both envs represent the same point in time

    //Initial state
    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    require validSwap(fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial, e1);
    require swapId == tokenId1Initial; //Assuming swapId is tokenId1
    
    require !isTokenPropOpened(e1, tokenId2Initial); // ensure tokenId2Initial doesn't have any opened swap proposals

    address tokenId1OwnerInitial = ownerOf(tokenId1Initial);
    address tokenId2OwnerInitial = ownerOf(tokenId2Initial);

    require tokenId1OwnerInitial == fromInitial && tokenId1OwnerInitial != 0;
    require tokenId2OwnerInitial == toInitial && tokenId2OwnerInitial != 0;

    //Store state before cancellation/rejection attempts
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


/***
    *NO NFT THEFT RULE: 
    * No party can end up owning an NFT they did not originally own without a successful swap.
    *
***/ 
rule noNftTheft(uint256 swapId) {
    env e; 
    require validEnv(e);

    //Initial state
    address fromInitial;
    address toInitial;
    uint256 tokenId1Initial;
    uint256 tokenId2Initial;
    uint256 deadlineInitial;
    address maliciousActor;

    require e.msg.sender == maliciousActor; 

    fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial = swapProp(swapId);
    require validSwap(fromInitial, toInitial, tokenId1Initial, tokenId2Initial, deadlineInitial, e);
    require swapId == tokenId1Initial; //Assuming swapId is tokenId1

    require maliciousActor == fromInitial || maliciousActor == toInitial; //malicious actor is one of the swap parties
    
    require !isTokenPropOpened(e, tokenId2Initial); // ensure tokenId2Initial doesn't have any opened swap proposals

    address tokenId1OwnerInitial = ownerOf(tokenId1Initial);
    address tokenId2OwnerInitial = ownerOf(tokenId2Initial);

    require tokenId1OwnerInitial == fromInitial && tokenId1OwnerInitial != 0;
    require tokenId2OwnerInitial == toInitial && tokenId2OwnerInitial != 0;
    //Execute any function 
    method f;
    calldataarg args; 
    require f.selector != sig:acceptTransfer(uint256).selector;
    if(f.selector == sig:acceptSwap(uint256,uint256).selector){
        acceptSwap(e, tokenId1Initial, tokenId2Initial);
    } else {
        f(e, args);
    }

    address tokenId1OwnerFinal = ownerOf(tokenId1Initial);
    address tokenId2OwnerFinal = ownerOf(tokenId2Initial);

    //In case malicious actor managed to change ownership of one NFT, he/she must have losed ownership of the other NFT
    assert (maliciousActor != tokenId1OwnerInitial && maliciousActor == tokenId1OwnerFinal) => (maliciousActor == tokenId2OwnerInitial && maliciousActor != tokenId2OwnerFinal);
}