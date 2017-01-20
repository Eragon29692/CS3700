README

high level approach:

After sending IAM NUID we loop (send and receive from server) until we receive the KEY: We have a buffer for message and what we receiv from socketfd goes to buffer. 
If the buffer contains a new line append starting from "INFO" in buffer to message (For in case the buffer is NULL 0000\nINFO 11111, we make sure to only append starting from the INFO ignoring the NULL part). 
IF there is no newline, we continue looping, appending any new message to buffer until we get a new line. We then reply with the appropriately message.

challenges:
- As C has no  proper string,  we had to manage the indexes of the character arrays.
- This also required us to get subString or append String through helper methods we defined.
- We had the error of sending too much garbage because we forget to set the correct length of the reply message (array size of 64).
    

We ran the code with our NUIDs multiple times (10+ times) and ensured the key was consistent. We also ran the sample NUID 001234567 and compared it to the key others were getting on Piazza (as suggested by the prof). 
We debugging our failures by printing out what error the server send back and was able to find the garbage sending along the send request. Also relying heavily on flags to find weird behavior in our code. 
