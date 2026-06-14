import { streamText } from 'ai'
import { createClient } from '@/lib/supabase/server'

export async function POST(req: Request) {
  const { messages, conversationId, searchContext } = await req.json()

  const supabase = await createClient()

  // Create or get conversation
  let convId = conversationId
  if (!convId) {
    const { data: conv, error } = await supabase
      .from('conversations')
      .insert({ title: messages[0]?.content?.slice(0, 50) || 'New Conversation' })
      .select()
      .single()

    if (error) {
      console.error('Error creating conversation:', error)
    } else {
      convId = conv.id
    }
  }

  // Save user message
  const lastUserMessage = messages[messages.length - 1]
  if (lastUserMessage && lastUserMessage.role === 'user' && convId) {
    await supabase.from('messages').insert({
      conversation_id: convId,
      role: 'user',
      content: lastUserMessage.content,
    })
  }

  // Build system prompt with search context
  let systemPrompt = `You are JARVIS, an advanced AI assistant inspired by Tony Stark's AI from Iron Man. 
You are highly intelligent, helpful, and speak with a slightly formal but warm British tone.
You address the user as "sir" or "ma'am" occasionally.
You are concise but thorough in your responses.
You have access to real-time information when needed.`

  if (searchContext && searchContext.length > 0) {
    systemPrompt += `\n\nHere is relevant real-time information from a web search:\n`
    searchContext.forEach((result: { title: string; snippet: string; link: string }, i: number) => {
      systemPrompt += `\n[${i + 1}] ${result.title}\n${result.snippet}\nSource: ${result.link}\n`
    })
    systemPrompt += `\nUse this information to provide an accurate and up-to-date response. Cite sources when appropriate.`
  }

  const result = streamText({
    model: 'openai/gpt-4o-mini',
    system: systemPrompt,
    messages,
    onFinish: async ({ text }) => {
      // Save assistant message
      if (convId) {
        await supabase.from('messages').insert({
          conversation_id: convId,
          role: 'assistant',
          content: text,
          search_context: searchContext || null,
        })
      }
    },
  })

  return result.toDataStreamResponse({
    headers: {
      'X-Conversation-Id': convId || '',
    },
  })
}
