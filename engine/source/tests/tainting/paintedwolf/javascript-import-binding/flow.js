import createExpress from "express";
import { Router as createRouter, json } from "express";
import * as framework from "express";
import differentDefault from "@other/express";
import { Router as differentNamed } from "@other/express";

function actualImports() {
  // ruleid: module-origin
  createExpress();
  // ruleid: module-origin
  createRouter();
  // ruleid: module-origin
  json();
  // ruleid: module-origin
  framework.Router();
  differentDefault();
  differentNamed();
}

function parameterShadows(createExpress, createRouter, json, framework) {
  createExpress();
  createRouter();
  json();
  framework.Router();
}

function localShadows() {
  const createExpress = () => ({});
  const createRouter = () => ({});
  const json = () => ({});
  const framework = { Router: () => ({}) };
  createExpress();
  createRouter();
  json();
  framework.Router();
}

function commonjsImports() {
  const express = require("express");
  const { Router: router } = require("express");
  // ruleid: module-origin
  express();
  // ruleid: module-origin
  router();
}
function shadowedRequire(require) {
  const express = require("express");
  const { Router: router } = require("express");
  express();
  router();
}
function lexicalRequire() {
  const express = require("express");
  const require = () => ({});
  express();
}
function blockImport() {
  { const express = require("express");
    // ruleid: module-origin
    express(); }
  express();
}

function destructuredRequire({ require }) {
  const express = require("express");
  express();
}
function nestedRequire({ loader: [require = () => ({})] }) {
  const express = require("express");
  express();
}
function restRequire(...require) {
  const express = require("express");
  express();
}
