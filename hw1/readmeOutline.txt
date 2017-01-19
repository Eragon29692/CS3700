README

high level approach:
loop:
- we have a buffer for message
- receive from socketfd go to buffer
- check buffer if it contain the new line
    - no newline -> append buffer to message -> back to loop
    - newline -> append starting from "INFO" of buffer to message (For in case buffer = NULL 0000\nINFO 11111, make sure only append starting from the INFO ... igonore the NULL part)
    	- Reply with the appropriately message

challenges:
- no proper string in C, so we have to managing the indexes of the character arrays
- no real string support so get subString or append String need to be defined as helper methods
- we had errors: 
    - sending too much garbage because we forget and get the len in send method as array size of 64
    


we tested the code agaisnt the server and make sure it ran multiple time correctly.
we debugging our failures by printing out what error the server send back and was able to find the garbage sending along the send request.
