import { handleConfig } from "../../lib/proxy.js";

export const onRequestGet = ({ request, env }) => handleConfig(request, env);
