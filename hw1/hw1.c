#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <netdb.h>

#define DEST_PORT 3700
#define MAX_SIZE 64


// Get the length of the array
int getLength(char buffer[], int size) {
    int i = 0;
    int count = 0;
    while(buffer[i] != '\0' && buffer[i] != '\n' && i < size) {
        count++;
        i++;
    }
    return count;
}

// Append the message to the string array
void appendString(char *buffer, char *message, int size) {
    int i = 0;
    int length = getLength(message, size);

    while((*(buffer + i) != '\0' && *(buffer + i) != '\n') && i < size) {
        if (length + i < size) {
            *(message + length + i) = *(buffer + i);
} i++;
}
    if (*(buffer + i) == '\n') {
        *(message + length + i) = '\n';
    } else {
        *(message + length + i) = '\0';
    }
}

// Checking for a new line character
int checkForNewline(char message[], int size) {
    int i = 0;
    int count = 0;
    while(i < size) {
        if (message[i] == '\n') {
            count++;
        }
        i++;
    }
    return count;
}
/ Add the new line character
void addNewline(char *buffer) {
    *(buffer + getLength(buffer, MAX_SIZE)) = '\n';
}

// Resetting an array
void resetArray(char *message, int size) {
    int i = 0;
    while(i < size) {
        *(message + i) = '\0';
        i++;
    }
}

//in case multiple message are sent, return the start of the last message
int startOfINFOMessage(char buffer[], int size) {
    int numberOfNewline = checkForNewline(buffer, size);
    //Only one or no newline chararcter
    if (numberOfNewline == 1 || numberOfNewline == 0) {
        return 0;
    }
    //more than one newline character
    int i = 0;
    while(i < size - 4 && buffer[i] != 'I' && buffer[i+1] != 'N' && buffer[i+2] != 'F' && buffer[i+3] != 'O') {
        i++;
    }
    return i;
}


int main(int argc, char* argv[]) {
    int port;
    char hostname[100] = "";
    char nuId[10] = "";
    struct hostent *host;

    // Getting port and NUID
    if (argc == 5 && strcmp(argv[1], "-p") == 0) {
        port = atoi(argv[2]);
        strcpy(hostname, argv[3]);
        strcpy(nuId, argv[4]);
    } else if (argc == 3) {
        port = DEST_PORT;
        strcpy(hostname, argv[1]);
        strcpy(nuId, argv[2]);
    } else {
        printf("\nWrong number of arguments!\n");
        return -1;
    }
    
    int sockfd;
    struct sockaddr_in dest_addr;
    char messageBuff[MAX_SIZE] = "";
    char buffer[MAX_SIZE] = "";
    char sendInfo[MAX_SIZE] = "";
    int looping = 1; //flag to stop while loops


    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        printf("\nCannot open socket");
        return -1;
    }
    host = gethostbyname(hostname);
    if (host == NULL) {
        printf("\nCan't get hostname's IP\n");
        return -1;
    }

     dest_addr.sin_family = AF_INET;     // host byte order
    dest_addr.sin_port = htons(port);   // short, network byte order
    memcpy(&dest_addr.sin_addr.s_addr, host->h_addr, host->h_length);


    if (connect(sockfd, (struct sockaddr *)&dest_addr, sizeof(struct sockaddr)) < 0) {
        printf("\nCannot open socket");
        return -1;
    } else {
        //wait for HELLO
        while(looping) {
            if (recv(sockfd, buffer, MAX_SIZE, 0) >= 0) {
                appendString(buffer, messageBuff, MAX_SIZE);
                if(checkForNewline(messageBuff, MAX_SIZE) != 0) {
                    looping = 0;
                    printf("\nReceive: %s\n", messageBuff);
                    resetArray(messageBuff, MAX_SIZE); //reset messageBuff
                    //SEND IAM NUID
                    char sendString[] = "IAM ";
                    appendString(nuId, sendString, MAX_SIZE);
                    addNewline(sendString);
                    printf("\nSend: %s\n", sendString);
                    send(sockfd, sendString, getLength(sendString, MAX_SIZE) + 1, 0);
                }
                resetArray(buffer, MAX_SIZE); //reset Buffer
            }
        }
        looping = 1;
        //respone to INFOs
        while(looping) {
            if (recv(sockfd, buffer, MAX_SIZE, 0) >= 0) {
                appendString((buffer + startOfINFOMessage(buffer, MAX_SIZE)), messageBuff, MAX_SIZE);

                if(checkForNewline(buffer, MAX_SIZE) != 0) {
                    printf("\nReceive: %s", messageBuff);

                    //NULL case
                    if (messageBuff[0]=='N' && messageBuff[1]=='U' && messageBuff[2]=='L' && messageBuff[3]=='L') {
                        resetArray(messageBuff, MAX_SIZE); //reset messageBuff
                    }

                    //KEY case
                    if(messageBuff[0]=='K' && messageBuff[1]=='E' && messageBuff[2]=='Y') {
                        printf("\nDone");
                        looping = 0;
                    }

                    //REPLY Case
                    if (messageBuff[0]=='I' && messageBuff[1]=='N' && messageBuff[2]=='F' && messageBuff[3]=='O') {
                        char sendString[] = "REPLY ";
                        appendString((messageBuff + 5), sendString, MAX_SIZE);
                        addNewline(sendString);
                        resetArray(messageBuff, MAX_SIZE); //reset messageBuff
                        printf("Send: %.*s\n\n", getLength(sendString, MAX_SIZE), sendString);
                        send(sockfd, sendString, getLength(sendString, MAX_SIZE) + 1, 0);
                    }

                }
                resetArray(buffer, MAX_SIZE); //reset Buffer
            }
        }
    }
    return 0;
}
