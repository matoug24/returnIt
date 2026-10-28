#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { ReturnetStack } from "../lib/returnet-stack";

const app = new cdk.App();
new ReturnetStack(app, "ReturnetPilotStack", {
  description: "Returnet pilot infrastructure. Synth only unless an authorized deployment is requested."
});

