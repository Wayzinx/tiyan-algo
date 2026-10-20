import { handleChat } from "../../lib/proxy.js";

export const onRequestPost = ({ request, env }) => handleChat(request, env);
