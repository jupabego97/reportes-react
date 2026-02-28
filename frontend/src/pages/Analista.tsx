import { useState, useRef, useEffect, type FormEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  MessageSquareText,
  Trash2,
  ChevronDown,
  Database,
  TableIcon,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { apiService } from '../services/api';
import { cn } from '../lib/utils';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sql?: string | null;
  datos?: Record<string, any>[] | null;
  error?: boolean;
}

const SUGGESTED_QUESTIONS = [
  '¿Cuál fue el producto más vendido este mes?',
  '¿Qué vendedor tiene el mayor margen?',
  '¿Cuáles productos tienen stock bajo?',
  '¿Cómo han sido las ventas por familia?',
  '¿Cuáles son los 10 productos con menor stock?',
  '¿Cuál es el margen promedio por proveedor?',
];

export function Analista() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || isLoading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const historial = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const result = await apiService.preguntarAnalista(question, historial);

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: result.respuesta,
        sql: result.sql,
        datos: result.datos,
        error: !!result.error,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: err.message || 'Error al procesar la consulta. Intenta de nuevo.',
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSuggestedClick = (question: string) => {
    setInput(question);
    inputRef.current?.focus();
  };

  const clearChat = () => {
    setMessages([]);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Sparkles className="h-8 w-8 text-primary" />
          Analista de Datos
        </h1>
        <p className="text-muted-foreground">
          Pregunta lo que quieras sobre tu negocio en lenguaje natural
        </p>
      </motion.div>

      {/* Chat Container */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <Card className="flex flex-col h-[calc(100vh-220px)]">
          <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <MessageSquareText className="h-5 w-5" />
              Chat
            </CardTitle>
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearChat}
                className="text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-4 w-4 mr-1" />
                Limpiar
              </Button>
            )}
          </CardHeader>

          <CardContent className="flex-1 overflow-y-auto px-4 pb-0">
            {/* Empty State */}
            {messages.length === 0 && !isLoading && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <Sparkles className="h-12 w-12 text-muted-foreground/40 mb-4" />
                <h3 className="text-lg font-medium mb-2">
                  Haz tu primera pregunta
                </h3>
                <p className="text-muted-foreground mb-6 max-w-md">
                  Puedo consultar tus datos de ventas, inventario, proveedores y
                  más. Pregunta en lenguaje natural y te respondo con datos reales.
                </p>
                <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => handleSuggestedClick(q)}
                      className="text-sm px-3 py-1.5 rounded-full border bg-background hover:bg-accent hover:text-accent-foreground transition-colors text-left"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Messages */}
            <div className="space-y-4 pb-4">
              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className={cn(
                      'flex',
                      msg.role === 'user' ? 'justify-end' : 'justify-start'
                    )}
                  >
                    {msg.role === 'user' ? (
                      <UserBubble content={msg.content} />
                    ) : (
                      <AssistantBubble message={msg} />
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Loading */}
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex justify-start"
                >
                  <div className="bg-muted rounded-2xl rounded-bl-md px-4 py-3 max-w-[85%]">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-sm">Analizando tus datos...</span>
                    </div>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </CardContent>

          {/* Input */}
          <div className="border-t p-4">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Escribe tu pregunta sobre el negocio..."
                disabled={isLoading}
                className="flex-1"
                autoFocus
              />
              <Button type="submit" disabled={isLoading || !input.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </Card>
      </motion.div>
    </div>
  );
}

function UserBubble({ content }: { content: string }) {
  return (
    <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-2.5 max-w-[85%]">
      <p className="text-sm whitespace-pre-wrap">{content}</p>
    </div>
  );
}

function AssistantBubble({ message }: { message: ChatMessage }) {
  const [showSql, setShowSql] = useState(false);
  const [showData, setShowData] = useState(false);

  return (
    <div
      className={cn(
        'rounded-2xl rounded-bl-md px-4 py-3 max-w-[85%] space-y-2',
        message.error
          ? 'bg-destructive/10 text-destructive'
          : 'bg-muted'
      )}
    >
      <div className="text-sm whitespace-pre-wrap leading-relaxed">
        {message.content}
      </div>

      {/* SQL Toggle */}
      {message.sql && (
        <div>
          <button
            onClick={() => setShowSql(!showSql)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <Database className="h-3 w-3" />
            <span>Ver SQL</span>
            <ChevronDown
              className={cn(
                'h-3 w-3 transition-transform',
                showSql && 'rotate-180'
              )}
            />
          </button>
          {showSql && (
            <motion.pre
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-2 p-3 rounded-lg bg-background/80 text-xs overflow-x-auto font-mono border"
            >
              {message.sql}
            </motion.pre>
          )}
        </div>
      )}

      {/* Data Table Toggle */}
      {message.datos && message.datos.length > 0 && (
        <div>
          <button
            onClick={() => setShowData(!showData)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <TableIcon className="h-3 w-3" />
            <span>Ver datos ({message.datos.length} filas)</span>
            <Badge variant="outline" className="text-[10px] px-1 py-0 ml-1">
              tabla
            </Badge>
            <ChevronDown
              className={cn(
                'h-3 w-3 transition-transform',
                showData && 'rotate-180'
              )}
            />
          </button>
          {showData && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-2 rounded-lg border overflow-hidden"
            >
              <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
                <DataTable data={message.datos} />
              </div>
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
}

function DataTable({ data }: { data: Record<string, any>[] }) {
  if (!data.length) return null;
  const columns = Object.keys(data[0]);

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((col) => (
            <TableHead key={col} className="text-xs whitespace-nowrap">
              {col}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row, i) => (
          <TableRow key={i}>
            {columns.map((col) => (
              <TableCell key={col} className="text-xs whitespace-nowrap">
                {formatValue(row[col])}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function formatValue(val: any): string {
  if (val === null || val === undefined) return '-';
  if (typeof val === 'number') {
    return val.toLocaleString('es-CO');
  }
  return String(val);
}
