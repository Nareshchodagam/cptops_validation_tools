/*
	This code is used by CPT to write patching related data to file "/etc/cptrelease".
	These are the content of file
	{
	"caseNumber": "012345",
	"patchingOwner": "sbhathej",
	"patchingStartTime": "02-26-2018 18:58:48",
	"patchingEndTime": "02-26-2018 18:59:02",
	"currentPatchBundle": "2018.01",
	"lastPatchBundle": "2017.11"
	}
*/

package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"strings"
)

const lastBundle = `/bin/grep VERSION /etc/sfdc-release | awk -F"-" '{print $3"."$4}'`

// Struct to create Json file
type cpt struct {
	CaseNumber         string `json:"caseNumber"`
	PatchingOwner      string `json:"patchingOwner"`
	PatchingstartTime  string `json:"patchingStartTime"`
	PatchingendTime    string `json:"patchingEndTime"`
	CurrentPatchBundle string `json:"currentPatchBundle"`
	LastPatchBundle    string `json:"lastPatchBundle"`
}

// Function to execute UNIX commands
func RunCommands(cmd string) (string, error) {
	cmdOut := exec.Command("bash", "-c", cmd)
	var stdout, stderr bytes.Buffer
	cmdOut.Stdout = &stdout
	cmdOut.Stderr = &stderr
	err := cmdOut.Run()
	if err != nil {
		err = fmt.Errorf("command %s failed with %s\n", cmd, err)
		return "", err
	}

	outStr, errStr := string(stdout.Bytes()), string(stderr.Bytes())
	if errStr != "" {
		err = fmt.Errorf("cmd.Run() failed with %s\n", errStr)
		return "", err
	}
	return outStr, nil
}

// Check sudo user
func CheckSudoUser() error {
	var user = os.Getenv("USER")
	if user != "root" {
		err := fmt.Errorf("error: sadly you need to run me as root")
		return err
	}
	return nil
}

// Function main
func main() {

	var cptrelease cpt

	err := CheckSudoUser()
	if err != nil {
		log.Fatal(err)

	}

	// Command line arguments
	bundle := flag.String("b", "", "Current OS Patchset")
	caseNum := flag.String("c", "", "GUS Change CaseNumber")
	last := flag.Bool("last", false, "Check last bundle")
	help := flag.Bool("h", false, "Command line help")

	flag.Parse()

	if *help {
		fmt.Println(`usage: write-cptrelease -b <current Bundle> -c <case_number>`)
		fmt.Println(`usage: write-cptrelease -last`)
		os.Exit(0)

	}

	// Get Timestamp
	timeStamp, err := RunCommands(`date '+%m-%d-%Y %H:%M:%S'`)
	if err != nil {
		log.Print(err)
	}
	timeStamp = strings.Trim(timeStamp, "\n")

	// To check if "/etc/cptrelease" file exists
	raw, err := ioutil.ReadFile("/etc/cptrelease")
	if err != nil {
		log.Printf("can't get the last patch bundle, %s", err)
	} else {
		err := json.Unmarshal(raw, &cptrelease)

		if err != nil {
			os.Exit(1)
		}
	}

	if *last {
		lastPatchBundle, err := RunCommands(lastBundle)

		if err != nil {
			log.Printf("%s", err)
		}

		cptrelease.LastPatchBundle = strings.Trim(lastPatchBundle, "\n")
		cptrelease.PatchingstartTime = string(timeStamp)
	} else {
		cptrelease = cpt{CaseNumber: *caseNum, PatchingOwner: os.Getenv("SUDO_USER"), PatchingendTime: string(timeStamp),
			CurrentPatchBundle: *bundle, LastPatchBundle: cptrelease.LastPatchBundle, PatchingstartTime: cptrelease.PatchingstartTime}
	}

	jsonData, err := json.MarshalIndent(cptrelease, "", "\t")

	f, err := os.Create("/etc/cptrelease")
	if err != nil {
		log.Fatal(err)
	}
	f.WriteString(string(jsonData))

	// use os.Chmod() function.
	err = os.Chmod("/etc/cptrelease", 0644)
	if err != nil {
		log.Println(err)
	}
	defer f.Close()

}
